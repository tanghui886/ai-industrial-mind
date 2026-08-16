"""审批工作台接口"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Approval, Notification, SchedulePlan
from ..permissions import require_perm

router = APIRouter(prefix="/approval", tags=["approval"])

TYPE_PRIORITY = {"全部类型": None, "排产变更": "排产变更", "紧急维修": "紧急维修",
                 "采购申请": "采购申请", "成本分摊": "成本分摊", "样箱插单": "样箱插单"}


def _approval_dict(a: Approval) -> dict:
    return {
        "id": a.id, "approval_no": a.approval_no, "approval_type": a.approval_type,
        "title": a.title, "priority": a.priority, "applicant": a.applicant,
        "applicant_role": a.applicant_role,
        "submitted_at": a.submitted_at.isoformat() if a.submitted_at else None,
        "status": a.status, "affect_lines": a.affect_lines,
        "expect_effect_time": a.expect_effect_time, "risk_level": a.risk_level,
        "related_agent": a.related_agent, "need_countersign": a.need_countersign,
        "detail": a.detail or {},
    }


@router.get("/list")
def list_approvals(status: str = "pending", type_filter: str = "全部类型",
                   keyword: str = "", db: Session = Depends(get_db)):
    q = db.query(Approval)
    if status == "pending":
        q = q.filter(Approval.status == "pending")
    elif status == "approved":
        q = q.filter(Approval.status == "approved")
    elif status == "rejected":
        q = q.filter(Approval.status == "rejected")
    if keyword:
        q = q.filter(Approval.title.contains(keyword) | Approval.approval_no.contains(keyword)
                     | Approval.applicant.contains(keyword))
    rows = q.order_by(Approval.submitted_at.desc()).all()
    tp = TYPE_PRIORITY.get(type_filter)
    if tp:
        rows = [r for r in rows if r.approval_type == tp]
    counts = {
        "pending": db.query(Approval).filter(Approval.status == "pending").count(),
        "approved": db.query(Approval).filter(Approval.status == "approved").count(),
        "rejected": db.query(Approval).filter(Approval.status == "rejected").count(),
    }
    return {"counts": counts, "items": [_approval_dict(a) for a in rows]}


@router.get("/{approval_id}")
def get_approval(approval_id: int, db: Session = Depends(get_db)):
    a = db.query(Approval).filter(Approval.id == approval_id).first()
    if not a:
        raise HTTPException(404, "审批单不存在")
    return _approval_dict(a)


class ActionReq(BaseModel):
    operator: str = "张主管"
    comment: str = ""


@router.post("/{approval_id}/approve")
def approve(approval_id: int, body: ActionReq, _: str = Depends(require_perm("approval.approve")),
            db: Session = Depends(get_db)):
    a = db.query(Approval).filter(Approval.id == approval_id).first()
    if not a:
        raise HTTPException(404, "审批单不存在")
    if a.status != "pending":
        raise HTTPException(400, "该审批单已处理")
    a.status = "approved"
    detail = dict(a.detail or {})
    timeline = detail.setdefault("timeline", [])
    timeline.append({"node": f"{body.operator} 审批通过 {('：' + body.comment) if body.comment else ''}",
                     "time": datetime.now().strftime("%Y-%m-%d %H:%M")})
    a.detail = detail
    # 联动：排产类审批通过后写入正式排产计划
    if a.target_type == "schedule_plan" and a.target_id:
        plan = db.query(SchedulePlan).filter(SchedulePlan.id == int(a.target_id)).first()
        if plan:
            plan.status = "confirmed"
            plan.approved_by = body.operator
            plan.approved_at = datetime.now()
    db.add(Notification(user_name=a.applicant, title="审批通过通知",
                        content=f"您的审批单 {a.approval_no}（{a.title}）已由 {body.operator} 审批通过。",
                        ntype="审批"))
    db.commit()
    return {"message": "审批通过"}


@router.post("/{approval_id}/reject")
def reject(approval_id: int, body: ActionReq, _: str = Depends(require_perm("approval.reject")),
           db: Session = Depends(get_db)):
    a = db.query(Approval).filter(Approval.id == approval_id).first()
    if not a:
        raise HTTPException(404, "审批单不存在")
    if a.status != "pending":
        raise HTTPException(400, "该审批单已处理")
    a.status = "rejected"
    detail = dict(a.detail or {})
    detail.setdefault("timeline", []).append({
        "node": f"{body.operator} 驳回{('：' + body.comment) if body.comment else ''}",
        "time": datetime.now().strftime("%Y-%m-%d %H:%M")})
    a.detail = detail
    if a.target_type == "schedule_plan" and a.target_id:
        plan = db.query(SchedulePlan).filter(SchedulePlan.id == int(a.target_id)).first()
        if plan:
            plan.status = "draft"
    db.add(Notification(user_name=a.applicant, title="审批驳回通知",
                        content=f"您的审批单 {a.approval_no}（{a.title}）已被 {body.operator} 驳回。",
                        ntype="审批"))
    db.commit()
    return {"message": "已驳回"}


@router.post("/{approval_id}/transfer")
def transfer(approval_id: int, body: ActionReq, _: str = Depends(require_perm("approval.transfer")),
             db: Session = Depends(get_db)):
    a = db.query(Approval).filter(Approval.id == approval_id).first()
    if not a:
        raise HTTPException(404, "审批单不存在")
    detail = dict(a.detail or {})
    detail.setdefault("timeline", []).append({
        "node": f"已转交给 {body.operator or '相关负责人'} 处理",
        "time": datetime.now().strftime("%Y-%m-%d %H:%M")})
    a.detail = detail
    db.commit()
    return {"message": "已转交"}
