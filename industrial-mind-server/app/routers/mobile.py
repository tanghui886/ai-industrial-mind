"""移动端专属接口：现场接单 / 我的订单 / 产能简报 / 通知"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Approval, IntentionOrder, Notification, ScheduleDaily, SchedulePlan
from ..permissions import require_perm
from ..services import planning_engine as engine
from ..services.intent import parse_intent
from ..services.llm import llm_parse_intent

router = APIRouter(prefix="/mobile", tags=["mobile"])

SAFETY_NOTE = "⚠️ 以上为AI辅助分析结果，仅供现场沟通参考。正式排产需经生产计划员确认后生效。"


class QuickOrderReq(BaseModel):
    text: str
    user: str = "张业务"
    voice_file: str | None = None


@router.post("/quick-order")
async def quick_order(body: QuickOrderReq, _: str = Depends(require_perm("workorder.add")),
                      db: Session = Depends(get_db)):
    """现场接单：自然语言 → 意图识别 → 排产可行性分析（需添加工令权限）"""
    llm_result = await llm_parse_intent(body.text)
    parsed = llm_result if (llm_result and llm_result.get("extracted_info")) else parse_intent(body.text)
    info = parsed["extracted_info"]
    intent = parsed.get("intent", "general_chat")

    if intent != "new_order_intent" or not info.get("box_type") or not info.get("quantity"):
        cap = None
        if intent == "capacity_query":
            import re
            m = re.search(r"(\d{1,2})月", body.text)
            today = date.today()
            month = int(m.group(1)) if m else today.month
            year = today.year if month >= today.month else today.year + 1
            cap = engine.capacity_summary(db, info.get("line_code") or "PD-D", year, month)
        return {"intent": intent, "confidence": parsed.get("confidence", 0.8),
                "message": "请按以下格式描述意向订单：箱型 + 数量 + 交付日期 + 交付地点，"
                           "例如「意向新订单，40HC箱型，总数量1000，计划2026.09.30交付，交付地点上海」",
                "capacity_brief": cap}

    dd = date.fromisoformat(info["delivery_date"]) if info.get("delivery_date") else date.today() + timedelta(days=30)
    analysis = engine.feasibility_analysis(db, info["box_type"], info["quantity"], dd,
                                           info.get("line_code") or "PD-D",
                                           info.get("delivery_location"))
    oi = analysis["order_info"]
    missing = [m for m in ["客户名称", "合同号", "接单属性", "内外贸属性"]
               if (m == "客户名称" and not info.get("customer")) or m != "客户名称"]

    return {
        "intent": intent,
        "confidence": parsed.get("confidence", 0.9),
        "order_info": oi,
        "schedule_analysis": analysis,
        "missing_fields": missing,
        "actions": ["confirm", "adjust", "view_schedule"],
        "safety_note": SAFETY_NOTE,
        "raw_extract": info,
    }


class ConfirmReq(BaseModel):
    box_type: str
    quantity: int
    delivery_date: str
    delivery_location: str = ""
    customer: str = ""
    input_text: str = ""
    teu: int = 0
    analysis: dict = {}
    user: str = "张业务"


@router.post("/quick-order/confirm")
def confirm(body: ConfirmReq, _: str = Depends(require_perm("workorder.add")),
            db: Session = Depends(get_db)):
    """确认录入意向订单（状态 pending，等待计划员处理，仅业务人员）"""
    io = IntentionOrder(
        intention_id=f"IO-{datetime.now().strftime('%Y-%m%d')}-{uuid.uuid4().hex[:6]}",
        source="mobile", input_text=body.input_text, box_type=body.box_type,
        quantity=body.quantity, delivery_date=date.fromisoformat(body.delivery_date),
        delivery_location=body.delivery_location, customer=body.customer or "待补充",
        teu=body.teu or int(body.quantity * 2), schedule_analysis=body.analysis,
        status="pending", created_by=body.user)
    db.add(io)
    db.flush()
    db.add(Notification(user_name="李计划", title="新意向订单待处理",
                        content=f"{body.user} 提交 {body.box_type} × {body.quantity}台意向订单"
                                f"（交付 {body.delivery_date}），请及时排产。", ntype="订单"))
    db.add(Notification(user_name=body.user, title="意向订单已录入",
                        content=f"已录入 {body.box_type} × {body.quantity}台，计划员将在1个工作日内确认排产。",
                        ntype="订单"))
    db.commit()
    return {"message": "已录入意向订单，计划员将在1个工作日内确认排产",
            "intention_id": io.intention_id, "safety_note": SAFETY_NOTE}


@router.get("/my-orders")
def my_orders(user: str = "张业务", db: Session = Depends(get_db)):
    rows = (db.query(IntentionOrder).filter(IntentionOrder.created_by == user)
            .order_by(IntentionOrder.created_at.desc()).all())
    status_cn = {"pending": "待确认", "confirmed": "已确认", "converted": "已转正式", "cancelled": "已取消"}
    return [{
        "intention_id": r.intention_id, "box_type": r.box_type, "quantity": r.quantity,
        "teu": r.teu, "delivery_date": r.delivery_date.isoformat() if r.delivery_date else None,
        "delivery_location": r.delivery_location, "customer": r.customer,
        "status": r.status, "status_cn": status_cn.get(r.status, r.status),
        "created_at": r.created_at.strftime("%m-%d %H:%M") if r.created_at else "",
        "input_text": r.input_text,
    } for r in rows]


@router.get("/capacity-brief")
def capacity_brief(line_code: str = "PD-D", month: str = "2026-08", db: Session = Depends(get_db)):
    summary = engine.capacity_summary(db, line_code, int(month[:4]), int(month[5:7]))
    days = engine.daily_utilization(db, line_code, int(month[:4]), int(month[5:7]))
    summary["days"] = [{"date": d["date"], "day": d["day"], "is_workday": d["is_workday"],
                        "hours": d["hours"], "day_of_week": d["day_of_week"],
                        "utilization": d["utilization"], "status": d["status"],
                        "booked_teu": d["booked_teu"],
                        "items": d["orders"]} for d in days]
    return summary


@router.get("/day-orders")
def day_orders(day: str, line_code: str = "PD-D", db: Session = Depends(get_db)):
    """某日工令明细（移动端排产查看）"""
    rows = (db.query(ScheduleDaily)
            .filter(ScheduleDaily.line_code == line_code, ScheduleDaily.schedule_date == date.fromisoformat(day))
            .all())
    return [{"work_order_no": r.work_order_no, "qty": r.planned_qty, "teu": r.teu} for r in rows]


@router.get("/notifications")
def notifications(user: str = "张业务", db: Session = Depends(get_db)):
    rows = (db.query(Notification).filter(Notification.user_name == user)
            .order_by(Notification.created_at.desc()).limit(20).all())
    return [{"id": n.id, "title": n.title, "content": n.content, "type": n.ntype,
             "created_at": n.created_at.strftime("%m-%d %H:%M") if n.created_at else "",
             "read": n.is_read} for n in rows]


@router.post("/share-report")
def share_report(body: dict):
    """生成分享摘要（演示：返回可复制的文本报告）"""
    return {"report": f"【ContainerMind 排产可行性报告】\n{body.get('text', '')}\n生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}"}


@router.get("/approvals")
def mobile_approvals(status: str = "pending", db: Session = Depends(get_db)):
    q = db.query(Approval).filter(Approval.status == status)
    rows = q.order_by(Approval.submitted_at.desc()).all()
    counts = {s: db.query(Approval).filter(Approval.status == s).count()
              for s in ("pending", "approved", "rejected")}
    return {"count": len(rows), "counts": counts, "items": [{
        "id": a.id, "approval_no": a.approval_no, "approval_type": a.approval_type,
        "title": a.title, "priority": a.priority, "applicant": a.applicant,
        "submitted_at": a.submitted_at.strftime("%m-%d %H:%M") if a.submitted_at else "",
        "detail": a.detail or {},
    } for a in rows]}


@router.post("/approvals/{approval_id}/approve")
def mobile_approve(approval_id: int, body: dict, _: str = Depends(require_perm("approval.approve")),
                   db: Session = Depends(get_db)):
    """移动端审批操作：action=approve/reject（需审批通过权限）"""
    action = body.get("action", "approve")
    a = db.query(Approval).filter(Approval.id == approval_id).first()
    if not a:
        raise HTTPException(404, "审批单不存在")
    if a.status != "pending":
        raise HTTPException(400, "该审批单已处理")
    operator = body.get("operator", "张主管")
    comment = body.get("comment", "")
    a.status = "approved" if action == "approve" else "rejected"
    detail = dict(a.detail or {})
    timeline = detail.setdefault("timeline", [])
    node = f"{operator} {'审批通过' if action == 'approve' else '驳回'}"
    if comment:
        node += f"：{comment}"
    timeline.append({"node": node, "time": datetime.now().strftime("%Y-%m-%d %H:%M")})
    a.detail = detail
    if action == "approve" and a.target_type == "schedule_plan" and a.target_id:
        plan = db.query(SchedulePlan).filter(SchedulePlan.id == int(a.target_id)).first()
        if plan:
            plan.status = "confirmed"
            plan.approved_by = operator
            plan.approved_at = datetime.now()
    db.add(Notification(user_name=a.applicant, title="审批结果通知",
                        content=f"您的审批单 {a.approval_no}（{a.title}）已由 {operator} "
                                f"{'审批通过' if action == 'approve' else '驳回'}。", ntype="审批"))
    db.commit()
    return {"message": "已通过" if action == "approve" else "已驳回",
            "new_status": a.status, "safety_note": SAFETY_NOTE}
