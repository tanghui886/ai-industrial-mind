"""子 Agent：智能排产 Scheduler —— 新订单可行性 / 产能查询 / 工令排产查询。

工具以 `SessionLocal()` 打开独立会话，供 LangChain 调用（线程安全、无副作用泄漏）。
langchain 仅在 make_scheduler_agent() 内按需导入，未安装时应用可继续走规则引擎兜底。
"""
from __future__ import annotations

import json
from datetime import date

from ..database import SessionLocal
from ..services import planning_engine as engine
from ..models import BoxType, ProductionLine, SchedulePlan

SYSTEM_PROMPT = """你是集装箱制造企业的「智能排产 Agent」。负责处理三类需求：
1. 新订单/意向订单排产可行性评估（new_order_intent）
2. 产线产能查询（capacity_query，如某月还有多少空位）
3. 工令/排产进度查询（schedule_query，如某工令排到几号）

规则约束：
- 必须先调用工具获得真实数据，再基于数据回答，不要凭空编造产能或排期。
- 产线编号需用标准编号（PD-D/BS-A/JS-A/JS-B/FX-A）；产线不存在时，调用
  list_lines 列出支持产线并请用户确认。
- 交付涉及排产变更，须在结尾注明需专业人员确认。
- 用户语句简洁、直接给结论；如需补充箱型/数量/交付日期等字段，先明确指出缺失字段。"""


def _db_result(data) -> str:
    """将业务 dict 序列化为给 LLM 的 JSON 文本。"""
    return json.dumps(data, ensure_ascii=False, default=str)


def _evaluate_feasibility(box_type: str, quantity: int,
                          delivery_date: str | None = None,
                          line_code: str = "PD-D",
                          delivery_location: str | None = None) -> str:
    """排产可行性评估：给定箱型、数量、计划交付日与产线，返回排产建议（建议排产期/日产能/交付缓冲/风险）。"""  # noqa: E501
    dd = None
    if delivery_date:
        try:
            dd = date.fromisoformat(delivery_date)
        except ValueError:
            return _db_result({"feasibility": "unknown", "message": f"交付日期格式无效: {delivery_date}"})
    db = SessionLocal()
    try:
        return _db_result(engine.feasibility_analysis(
            db, box_type, quantity, dd, line_code, delivery_location))
    finally:
        db.close()


def _query_capacity(line_code: str, month: int, year: int | None = None) -> str:
    """产能查询：给定产线编号、月份（1-12），返回该月计划/已排/剩余空位（TEU）、利用率、分日空位明细。"""  # noqa: E501
    today = date.today()
    year = year or (today.year if month >= today.month else today.year + 1)
    db = SessionLocal()
    try:
        line_row = db.query(ProductionLine).filter(ProductionLine.line_code == line_code).first()
        if not line_row:
            lines = db.query(ProductionLine).order_by(ProductionLine.line_code).all()
            return _db_result({"error": "产线不存在", "supported_lines": lines and [
                {"line_code": l.line_code, "line_name": l.line_name} for l in lines]})
        return _db_result(engine.capacity_summary(db, line_code, year, month))
    finally:
        db.close()


def _query_schedule(line_code: str | None = None, work_order_no: str | None = None,
                    box_type: str | None = None, month: int | None = None) -> str:
    """排产查询：按工令号，或按产线+箱型+月份查询排产工令列表（起始/结束日期与状态）。"""  # noqa: E501
    today = date.today()
    db = SessionLocal()
    try:
        if work_order_no:
            rows = db.query(SchedulePlan).filter(SchedulePlan.work_order_no == work_order_no).all()
        else:
            q = db.query(SchedulePlan)
            if line_code:
                q = q.filter(SchedulePlan.line_code == line_code)
            if box_type:
                q = q.filter(SchedulePlan.box_type == box_type)
            if month:
                year = today.year if month >= today.month else today.year + 1
                q = q.filter(SchedulePlan.plan_month == f"{year:04d}-{month:02d}")
            rows = q.order_by(SchedulePlan.start_date).all()
        status_map = {'draft': '草稿', 'pending_approval': '待审批', 'confirmed': '已确认', 'completed': '已完成'}
        return _db_result([{
            "work_order_no": r.work_order_no, "box_type": r.box_type, "quantity": r.quantity,
            "customer": r.customer, "start_date": r.start_date.isoformat() if r.start_date else None,
            "end_date": r.end_date.isoformat() if r.end_date else None,
            "status": status_map.get(r.status, r.status),
        } for r in rows[:20]])
    finally:
        db.close()


def _list_lines() -> str:
    """列出系统支持的产线（编号+名称）。"""
    db = SessionLocal()
    try:
        rows = db.query(ProductionLine).order_by(ProductionLine.line_code).all()
        return _db_result([{"line_code": l.line_code, "line_name": l.line_name}
                           for l in rows])
    finally:
        db.close()


def _get_box_type(code: str) -> str:
    """查询箱型的日产能标准（min~max/std）与 TEU 系数。"""
    db = SessionLocal()
    try:
        box = db.query(BoxType).filter(BoxType.code == code).first()
        if not box:
            return _db_result({"error": f"未识别箱型 {code}"})
        return _db_result({"code": box.code, "name": box.name,
                           "daily_capacity_min": box.daily_capacity_min,
                           "daily_capacity_max": box.daily_capacity_max,
                           "daily_capacity_std": box.daily_capacity_std,
                           "teu_factor": box.teu_factor})
    finally:
        db.close()


def make_scheduler_agent() -> dict:
    """构建规范化的子 Agent 配置（供主 Agent 作为 subagents 注册）。langchain 按需导入。"""
    from langchain.tools import tool
    return {
        "name": "scheduler",
        "description": "智能排产：新订单排产可行性评估、产线产能查询、工令排产进度查询。",
        "system_prompt": SYSTEM_PROMPT,
        "tools": [tool(f) for f in (_evaluate_feasibility, _query_capacity, _query_schedule,
                                    _list_lines, _get_box_type)],
    }