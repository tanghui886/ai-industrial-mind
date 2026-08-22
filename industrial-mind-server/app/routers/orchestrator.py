"""编排层 Orchestrator：统一对话入口（意图识别 → Agent 路由 → SSE 流式输出）"""
from __future__ import annotations

import asyncio
import json
import re
from datetime import date

from fastapi import APIRouter, Depends, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..agents import ENABLE_DEEP_AGENTS, chat as agents_deep_chat
from ..agents.base import AGENT_DISPLAY
from ..database import get_db
from ..models import ChatMessage, ChatSession, SchedulePlan
from ..services import planning_engine as engine
from ..services.intent import parse_intent
from ..services.llm import llm_parse_intent, chat_completion
from .device import _gen_devices

router = APIRouter(prefix="/orchestrator", tags=["orchestrator"])

SAFETY_NOTE = "⚠️ 以上内容由 AI Agent 辅助生成，仅供辅助参考。涉及排产变更、设备操作、产线停机等决策，必须由具备资质的专业人员确认后执行。"

AGENT_NAME = {"new_order_intent": "智能排产 Agent（Scheduler）",
              "capacity_query": "智能排产 Agent（Scheduler）",
              "schedule_query": "智能排产 Agent（Scheduler）",
              "device_query": "设备诊断 Agent",
              "material_gap": "物料缺口 Agent",
              "storage_risk": "堆存风险 Agent",
              "cost_analysis": "成本动因 Agent",
              "general_chat": "其他 Agent（编排）"}


class ChatReq(BaseModel):
    message: str
    session_id: str = "default"
    source: str = "pc"
    user: str = ""
    context: dict = {}


class IntentParseReq(BaseModel):
    text: str


def _fmt_analysis(analysis: dict) -> str:
    oi = analysis.get("order_info", {})
    sug = analysis.get("schedule_suggestion", {})
    dl = analysis.get("delivery_assessment", {})
    lines = [
        f"排产可行性：{analysis.get('feasibility')}（置信度 {analysis.get('feasibility_score')}）",
        f"订单：{oi.get('box_type_display', oi.get('box_type'))} × {oi.get('quantity')}台 ≈ {oi.get('teu')} TEU，日产能 {oi.get('daily_capacity')}台/天",
    ]
    if sug.get("recommended_start"):
        lines.append(f"建议排产期：{sug['recommended_start']} ~ {sug['recommended_end']}（{sug.get('note', '')}）")
    lines.append(f"交付评估：{dl.get('estimated_delivery')} 交付，缓冲 {dl.get('buffer_days')} 天（风险 {dl.get('risk_level')}）")
    for r in (analysis.get("risk_alerts") or [])[:3]:
        lines.append(f"⚠️ {r}")
    return "\n".join(lines)


def build_response(message: str, db: Session, llm_result: dict | None = None,
                   today: date | None = None) -> dict:
    today = today or date.today()
    parsed = parse_intent(message, today)
    intent = parsed["intent"]
    info = parsed["extracted_info"]
    # LLM 意图识别结果优先参与决策（覆盖规则引擎抽取的产线等字段）
    llm_info = (llm_result or {}).get("extracted_info") or {}
    if llm_result and llm_result.get("intent"):
        intent = llm_result["intent"]
    for k, v in llm_info.items():
        if v not in (None, "", False):
            info[k] = v
    line = info.get("line_code") or "PD-D"
    card, text = None, ""

    if intent == "new_order_intent" and info.get("box_type") and info.get("quantity"):
        dd = date.fromisoformat(info["delivery_date"]) if info.get("delivery_date") else None
        analysis = engine.feasibility_analysis(db, info["box_type"], info["quantity"], dd,
                                               line, info.get("delivery_location"), today=today)
        card = {"type": "feasibility", "title": "排产可行性评估", "data": analysis}
        text = _fmt_analysis(analysis)
    elif intent == "capacity_query":
        m = re.search(r"(\d{1,2})月", message)
        month = int(m.group(1)) if m else today.month
        year = today.year if month >= today.month else today.year + 1
        # 校验产线是否存在
        from ..models import BoxType, ProductionLine
        line_row = db.query(ProductionLine).filter(ProductionLine.line_code == line).first()
        if not line_row:
            text = (f"未找到产线「{line}」。当前系统支持的产线有："
                    + "、".join(f"{l.line_code}（{l.line_name}）"
                                for l in db.query(ProductionLine).order_by(ProductionLine.line_code).all())
                    + "。请确认产线编号后重试。")
            card = None
        else:
            summary = engine.capacity_summary(db, line, year, month)
            box_code = info.get("box_type")
            extra = ""
            if box_code:
                box = db.query(BoxType).filter(BoxType.code == box_code).first()
                if box:
                    extra = f"\n{box.code}（{box.name}）日产能标准：{box.daily_capacity_min}~{box.daily_capacity_max} 台/天（标准值 {box.daily_capacity_std}）。"
            card = {"type": "capacity", "title": f"{line} {year}年{month}月 产能概况", "data": summary}
            text = (f"{line} {year}年{month}月：计划 {summary['plan_teu']} TEU，已排 {summary['scheduled_teu']} TEU，"
                    f"剩余空位 {summary['remaining_teu']} TEU，利用率 {summary['utilization_rate']}%，"
                    f"工作日 {summary['workdays']} 天，冲突 {summary['conflict_days']} 天。{extra}")
            # 分日空位明细
            daily_free = summary.get("daily_free") or []
            free_days = [d for d in daily_free if d["remaining_teu"] > 0]
            if free_days:
                detail = "；".join(
                    f"{d['date'][5:]} 空位 {d['remaining_teu']} TEU（日产能 {d['capacity']}，已排 {d['booked_teu']}）"
                    for d in free_days)
                text += f"\n分日空位明细：{detail}"
            else:
                text += "\n暂无分日期的空位明细。"
    elif intent == "schedule_query":
        wo = info.get("work_order_no")
        if wo:
            orders = db.query(SchedulePlan).filter(SchedulePlan.work_order_no == wo).all()
        else:
            orders = []
            q = db.query(SchedulePlan).filter(SchedulePlan.line_code == line)
            if info.get("box_type"):
                q = q.filter(SchedulePlan.box_type == info["box_type"])
            m = re.search(r"(\d{1,2})月", message)
            if m:
                month = int(m.group(1))
                year = today.year if month >= today.month else today.year + 1
                q = q.filter(SchedulePlan.plan_month == f"{year:04d}-{month:02d}")
            orders = q.order_by(SchedulePlan.start_date).all()
        if orders:
            rows = [f"{o.work_order_no}（{o.box_type} × {o.quantity}台）：{o.start_date} ~ {o.end_date}，"
                    f"状态「{ {'draft':'草稿','pending_approval':'待审批','confirmed':'已确认','completed':'已完成'}.get(o.status, o.status)}」"
                    for o in orders[:8]]
            text = "查询到以下工令排产：\n" + "\n".join(rows)
            card = {"type": "work_orders", "title": "排产查询结果", "data": orders[:8] and [
                {"work_order_no": o.work_order_no, "box_type": o.box_type, "quantity": o.quantity,
                 "start_date": o.start_date.isoformat(), "end_date": o.end_date.isoformat(),
                 "status": o.status, "customer": o.customer} for o in orders[:8]]}
        else:
            text = "未查询到匹配的工令，请提供工令号（如 SHPD-2026-281-DS）或箱型+月份。"
    elif intent == "device_query":
        devices = _gen_devices(db)
        abnormal = [d for d in devices if d["status"] != "正常"]
        line = info.get("line_code")
        if line:
            # 指定产线：校验产线是否存在
            from ..models import ProductionLine
            line_row = db.query(ProductionLine).filter(ProductionLine.line_code == line).first()
            if not line_row:
                text = (f"未找到产线「{line}」。当前系统支持的产线有："
                        + "、".join(f"{l.line_code}（{l.line_name}）"
                                    for l in db.query(ProductionLine).order_by(ProductionLine.line_code).all())
                        + "。请确认产线编号后重试。")
                card = None
            else:
                abnormal = [d for d in abnormal if d["line_code"] == line]
                card = {"type": "devices", "title": f"{line} 产线异常设备", "data": abnormal,
                        "scope": "line", "line_code": line}
                if abnormal:
                    text = (f"{line} 产线共 {len(abnormal)} 台异常设备：\n"
                            + "\n".join(
                                f"- {d['device_id']}（{d['name']}，{d['device_type']}）：状态「{d['status']}」，"
                                f"健康度 {d['health']}，温度 {d['temperature']}℃，振动 {d['vibration']}mm/s，"
                                f"负载 {d['current_load']}%（下次保养 {d['next_maintenance']}）"
                                for d in abnormal))
                else:
                    text = f"{line} 产线所有设备运行正常，暂无异常设备。"
        else:
            # 未指定产线：按产线分类汇总异常设备
            by_line = {}
            for d in abnormal:
                by_line.setdefault(d["line_code"], []).append(d)
            card = {"type": "devices", "title": "各产线异常设备汇总", "data": abnormal, "scope": "all"}
            if abnormal:
                parts = []
                for lc in sorted(by_line):
                    ds = by_line[lc]
                    parts.append(f"{lc}：{len(ds)} 台异常")
                text = (f"共 {len(abnormal)} 台异常设备，按产线汇总：\n" + "\n".join(f"- {p}" for p in parts))
            else:
                text = "所有产线设备运行正常，暂无异常设备。"
    elif intent == "material_gap":
        from .agents import material_gap as _agent_gap
        data = _agent_gap(db=db)
        card = {"type": "material_gap", "title": "物料缺口", "data": data}
        gaps = [r for r in data.get("gaps") or [] if r["gap"] > 0]
        if gaps:
            text = (f"{data.get('summary')}：\n"
                    + "\n".join(f"- {r['material']}（{r['factory']}）：缺口 {r['gap']}{r['unit'] or '台'}，"
                                f"在库 {r['in_stock']}，订单扣减 {r['order_deducted']}。建议：{r['action']}"
                                for r in gaps))
        else:
            text = "当前各物料库存均可满足排产需求，暂无物料缺口。"
    elif intent == "storage_risk":
        from .agents import storage_risk as _agent_storage
        data = _agent_storage(db=db)
        card = {"type": "storage_risk", "title": "堆存风险", "data": data}
        risks = [r for r in data.get("lines") or [] if r["status"] == "风险"]
        if risks:
            text = (f"{data.get('summary')}：\n"
                    + "\n".join(f"- {r['line_code']}（{r['line_name']}）：总容纳 {r['capacity']}，"
                                f"堆存 {r['storage_units']}，预堆存 {r['pre_storage']}，剩余 {r['remaining']}（爆仓）"
                                for r in risks))
        else:
            text = "各产线堆存均有足够剩余空间，未发现爆仓风险。"
    elif intent == "cost_analysis":
        from .agents import cost_analysis as _agent_cost
        data = _agent_cost(db=db)
        card = {"type": "cost", "title": "成本动因分析", "data": data}
        items = data.get("per_box_cost") or []
        text = (f"{data.get('month')} 单箱成本拆解：\n"
                + "\n".join(f"- {i['item']} ¥{i['amount']}（占比 {i.get('ratio', '')}，动因：{i.get('driver', '')}）" for i in items))
        if data.get("anomaly"):
            text += "\n异常：\n" + "\n".join(f"- {a}" for a in data["anomaly"])
    else:
        text = ("我是 ContainerMind 工业协同 Agent，可以帮您：\n"
                "1. 排产可行性评估：例如「意向新订单，40HC箱型 1000台，9月30日交付上海」\n"
                "2. 产能查询：例如「9月份PD-D线还有多少空位」\n"
                "3. 排产查询：例如「SHPD-2026-281-DS排到几号了」\n"
                "4. 物料缺口：例如「当前各产线物料缺口情况如何」\n"
                "5. 堆存风险：例如「哪些产线的堆存存在爆仓风险」\n"
                "6. 成本动因：例如「本月成本动因分析」")

    return {
        "intent": intent,
        "intent_label": {"new_order_intent": "智能排产", "capacity_query": "智能排产",
                         "schedule_query": "智能排产", "device_query": "设备诊断",
                         "material_gap": "物料缺口", "storage_risk": "堆存风险",
                         "cost_analysis": "成本动因", "general_chat": "其他"}[intent],
        "confidence": parsed["confidence"],
        "agent": AGENT_NAME[intent],
        "extracted_info": info,
        "missing_fields": parsed["missing_fields"],
        "reply_text": text,
        "card": card,
        "suggestions": ["按交期倒排", "规避检修日", "替代物料方案", "分批交付方案"],
        "safety_note": SAFETY_NOTE,
    }


async def _llm_refine_reply(result: dict, message: str, user: str = "anonymous",
                            session_id: str = "default") -> str | None:
    """用 LLM 对查询结果做自然语言总结（未配置 LLM 或失败时返回 None，保留规则文本）"""
    if not result.get("card"):
        return None
    card = result["card"]
    if card.get("type") == "capacity":
        d = card["data"]
        daily = d.get("daily_free") or []
        free_days = [x for x in daily if x.get("remaining_teu", 0) > 0]
        if free_days:
            daily_lines = "\n".join(
                f"- {x['date'][5:]}：空位 {x['remaining_teu']} TEU（日产能 {x['capacity']}，已排 {x['booked_teu']}）"
                for x in free_days)
        else:
            daily_lines = "（本月暂无分日期的空位明细）"
        prompt = (f"用户问：{message}\n\n"
                  f"以下是 {d.get('line_code')} 产线 {d.get('month')} 月产能数据：\n"
                  f"计划 {d.get('plan_teu')} TEU，已排 {d.get('scheduled_teu')} TEU，"
                  f"剩余空位 {d.get('remaining_teu')} TEU，利用率 {d.get('utilization_rate')}%，"
                  f"工作日 {d.get('workdays')} 天，冲突 {d.get('conflict_days')} 天。\n"
                  f"分日空位明细：\n{daily_lines}\n"
                  "请用中文、简洁自然地回答用户问题，先给出总剩余空位，再按日期列出有剩余空位的日期及其空位产能数；"
                  "若没有分日空位则说明「暂无分日期的空位明细」。不要重复数据结构。")
    elif card.get("type") == "work_orders":
        d = card["data"]
        rows = "\n".join(f"- {o.get('work_order_no')}（{o.get('box_type')}×{o.get('quantity')}台，"
                         f"{o.get('start_date')}~{o.get('end_date')}，{o.get('status')}）" for o in d)
        prompt = f"用户问：{message}\n\n查询到的工令排产：\n{rows}\n请用中文简洁总结。"
    elif card.get("type") == "devices":
        d = card["data"]
        scope, lc = card.get("scope"), card.get("line_code")
        if not d:
            prompt = f"用户问：{message}\n\n{lc or '所有产线'} 暂无异常设备，所有设备运行正常。请用中文简洁告知用户设备状态良好。"
        else:
            lines = []
            if scope == "line":
                lines.append(f"产线 {lc} 异常设备（共 {len(d)} 台）：")
                for dev in d:
                    lines.append(f"- {dev.get('device_id')}（{dev.get('name')}，{dev.get('device_type')}）："
                                 f"状态「{dev.get('status')}」，健康度 {dev.get('health')}，"
                                 f"温度 {dev.get('temperature')}℃，振动 {dev.get('vibration')}mm/s，"
                                 f"负载 {dev.get('current_load')}%，下次保养 {dev.get('next_maintenance')}")
            else:
                by_line = {}
                for dev in d:
                    by_line.setdefault(dev.get("line_code"), []).append(dev)
                lines.append(f"各产线异常设备汇总（共 {len(d)} 台）：")
                for code in sorted(by_line):
                    ds = by_line[code]
                    lines.append(f"- {code}：{len(ds)} 台异常")
                    for dev in ds:
                        lines.append(f"    · {dev.get('device_id')}（{dev.get('name')}，{dev.get('device_type')}）："
                                     f"状态「{dev.get('status')}」，健康度 {dev.get('health')}")
            prompt = (f"用户问：{message}\n\n设备异常数据如下：\n"
                      + "\n".join(lines) +
                      "\n请用中文简洁、专业地总结。若指定了产线，按设备逐台说明异常状态与健康度；"
                      "若未指定产线，按产线分类汇总异常设备数量，并指出状态最差的几家设备。直接给结论，不要重复原始数据结构。")
    elif card.get("type") == "material_gap":
        d = card["data"]
        gaps = "\n".join(
            f"- {x.get('material')}（{x.get('factory')}）：缺口 {x.get('gap')}{x.get('unit') or '台'}，"
            f"在库 {x.get('in_stock')}，订单扣减 {x.get('order_deducted')} → {x.get('action')}"
            for x in (d.get("gaps") or []) if x.get("gap", 0) > 0) or "（无物料缺口）"
        prompt = (f"用户问：{message}\n\n物料缺口数据：\n{d.get('summary', '')}\n{gaps}\n"
                  "请用中文简洁总结存在缺口的物料、缺口数量与补货建议，按缺口量从大到小排序。直接给结论。")
    elif card.get("type") == "storage_risk":
        d = card["data"]
        rows = "\n".join(
            f"- {x.get('line_code')}（{x.get('line_name')}）：总容纳 {x.get('capacity')}，堆存 {x.get('storage_units')}，"
            f"预堆存 {x.get('pre_storage')}，剩余 {x.get('remaining')}"
            for x in (d.get("lines") or [])) or "（无数据）"
        prompt = (f"用户问：{message}\n\n堆存数据：\n{rows}\n"
                  "请用中文简洁总结哪些产线存在爆仓风险及其剩余空间，指出最紧张的产线并给出建议。直接给结论。")
    elif card.get("type") == "cost":
        d = card["data"]
        items = "\n".join(f"- {x.get('item')} ¥{x.get('amount')}（占比 {x.get('ratio')}，动因 {x.get('driver')}）"
                          for x in (d.get("per_box_cost") or []))
        anomaly = "、".join(d.get("anomaly") or [])
        prompt = (f"用户问：{message}\n\n{d.get('month')} 单箱成本拆解数据：\n{items}\n"
                  f"异常项：{anomaly}\n"
                  "请用中文简洁总结成本构成、主要成本动因与异常项，指出成本优化的方向。直接给结论。")
    else:
        return None
    content = await chat_completion(
        [{"role": "system", "content": "你是集装箱制造企业的排产计划助手，回答要简洁、专业、直接给结论。"},
         {"role": "user", "content": prompt}], scene="refine", user=user, session_id=session_id)
    return content or None


INTENT_LABEL = {"new_order_intent": "智能排产", "capacity_query": "智能排产",
                "schedule_query": "智能排产", "device_query": "设备诊断",
                "material_gap": "物料缺口", "storage_risk": "堆存风险",
                "cost_analysis": "成本动因", "general_chat": "其他"}


async def _deep_agent_result(message: str, user: str, session_id: str) -> dict | None:
    """优选路径：调用 deepagents 主 Agent 编排各子 Agent。成功返回与 build_response 兼容的
    结果（reply_text 为编排出文），失败/未启用返回 None 由规则引擎兜底。"""
    if not ENABLE_DEEP_AGENTS:
        return None
    parsed = parse_intent(message)
    text = await agents_deep_chat(message, session_id=session_id, user=user)
    if not text:
        return None
    intent = parsed["intent"]
    return {
        "intent": intent,
        "intent_label": INTENT_LABEL.get(intent, "其他"),
        "confidence": parsed["confidence"],
        "agent": AGENT_DISPLAY,
        "extracted_info": parsed["extracted_info"],
        "missing_fields": parsed["missing_fields"],
        "reply_text": text,
        "card": None,
        "suggestions": ["按交期倒排", "规避检修日", "替代物料方案", "分批交付方案"],
        "safety_note": SAFETY_NOTE,
        "engine": "deepagents · 多智能体编排",
    }


async def _ensure_session(db: Session, user: str, session_id: str, message: str) -> None:
    """确保会话存在；新会话自动创建并以其首条消息生成标题"""
    if session_id in ("default", "", "new"):
        return
    if not db.query(ChatSession).filter(ChatSession.session_id == session_id).first():
        title = message.strip()[:20] or "新会话"
        db.add(ChatSession(session_id=session_id, user=user, title=title))
        db.commit()


def _save_messages(db: Session, user: str, session_id: str, message: str, result: dict) -> None:
    """保存用户消息与 Agent 回复到 chat_message 表"""
    if session_id in ("default", "", "new"):
        return
    db.add(ChatMessage(session_id=session_id, user=user, role="user", content=message))
    db.add(ChatMessage(
        session_id=session_id, user=user, role="agent",
        content=result.get("reply_text", ""),
        card=result.get("card") if isinstance(result.get("card"), dict) else {},
        intent_label=result.get("intent_label", ""),
        agent=result.get("agent", ""),
    ))
    # 更新会话标题与时间
    sess = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
    if sess:
        if sess.title == "新会话" and message:
            sess.title = message.strip()[:20]
        db.commit()
    else:
        db.commit()


@router.post("/chat")
async def chat(body: ChatReq, db: Session = Depends(get_db),
               x_username: str | None = Header(default=None, alias="X-Username")):
    user = (x_username or body.user or "anonymous").strip() or "anonymous"
    _ensure_session(db, user, body.session_id, body.message)
    # 优选 deepagents 多智能体编排；失败/未启用时回落 LLM 意图识别 + 规则引擎
    result = await _deep_agent_result(body.message, user=user, session_id=body.session_id)
    if result is None:
        llm_result = await llm_parse_intent(body.message, user=user, session_id=body.session_id)
        result = build_response(body.message, db, llm_result)
        refined = await _llm_refine_reply(result, body.message, user=user, session_id=body.session_id)
        if refined:
            result["reply_text"] = refined
        if llm_result and llm_result.get("intent"):
            result["llm_intent"] = llm_result
            result["engine"] = "deepseek-v4-flash-0731 + 规则引擎"
        else:
            result["engine"] = "内置规则引擎（未配置 LLM API Key，可在 .env 中配置）"
    _save_messages(db, user, body.session_id, body.message, result)
    return result


@router.post("/chat/stream")
async def chat_stream(body: ChatReq, db: Session = Depends(get_db),
                      x_username: str | None = Header(default=None, alias="X-Username")):
    """SSE 流式输出：思考过程 + 结构化结果"""
    user = (x_username or body.user or "anonymous").strip() or "anonymous"
    _ensure_session(db, user, body.session_id, body.message)
    return await _sse_response(body.message, db, user, body.session_id)


@router.get("/chat/stream")
async def chat_stream_get(payload: str, db: Session = Depends(get_db),
                          x_username: str | None = Header(default=None, alias="X-Username")):
    """SSE GET 版（供前端 EventSource 使用）：payload 为 JSON 字符串"""
    try:
        body = ChatReq(**json.loads(payload))
    except Exception:
        body = ChatReq(message=str(payload))
    # EventSource 无自定义请求头，用户身份从 payload 中取得（请求头优先）
    user = (x_username or body.user or "anonymous").strip() or "anonymous"
    _ensure_session(db, user, body.session_id, body.message)
    return await _sse_response(body.message, db, user, body.session_id)


async def _sse_response(message: str, db, user: str = "anonymous", session_id: str = "default"):
    result = await _deep_agent_result(message, user=user, session_id=session_id)
    if result is None:
        llm_result = await llm_parse_intent(message, user=user, session_id=session_id)
        result = build_response(message, db, llm_result)
        refined = await _llm_refine_reply(result, message, user=user, session_id=session_id)
        if refined:
            result["reply_text"] = refined
    _save_messages(db, user, session_id, message, result)

    async def gen():
        def ev(t: str, p: dict):
            return f"event: {t}\ndata: {json.dumps(p, ensure_ascii=False, default=str)}\n\n"

        yield ev("intent", {"intent": result["intent"], "intent_label": result["intent_label"],
                            "confidence": result["confidence"], "agent": result["agent"]})
        steps = ["理解输入意图…", "加载排产日历与产能约束…", "调用排产计划 Agent 分析中…",
                 "校验物料齐套与交付风险…", "生成结构化结论…"]
        for s in steps:
            await asyncio.sleep(0.35)
            yield ev("thinking", {"text": s})
        await asyncio.sleep(0.3)
        yield ev("result", result)
        yield ev("done", {"safety_note": SAFETY_NOTE})

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.post("/intent-parse")
async def intent_parse(body: IntentParseReq):
    llm_result = await llm_parse_intent(body.text)
    if llm_result:
        return llm_result
    return parse_intent(body.text)
