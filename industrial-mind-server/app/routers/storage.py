"""堆存信息：按产线统计堆存容量与风险（来源：production_line + schedule_plan）"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Factory, ProductionLine, SchedulePlan

router = APIRouter(prefix="/storage", tags=["storage"])


class CapacityIn(BaseModel):
    line_code: str
    storage_capacity: int


@router.get("/list")
def storage_list(db: Session = Depends(get_db)):
    """各厂、产线堆存统计：
    - 总容纳数量 storage_capacity：产线可手工设置
    - 堆存数量 storage_units = 该产线所有「已确认(confirmed)」工令数量合计
    - 预堆存 pre_storage = 该产线「待审批/审批中(pending_approval) + 草稿(draft)」工令数量合计
    - 剩余空间 remaining = 总容纳 - 堆存 - 预堆存
    - 状态 status：爆仓(remaining<0) → 风险；有空余(remaining>=0) → 正常
    """
    factory_names = {f.factory_code: f.factory_name for f in db.query(Factory).all()}
    lines = db.query(ProductionLine).order_by(ProductionLine.factory_code, ProductionLine.id).all()

    storage_units: dict[str, int] = {}  # 已确认工令
    pre_storage: dict[str, int] = {}    # 待审批/审批中 + 草稿工令
    for code, qty, status in (db.query(SchedulePlan.line_code, SchedulePlan.quantity,
                                       SchedulePlan.status).all()):
        if status == "confirmed":
            storage_units[code] = storage_units.get(code, 0) + qty
        elif status in ("pending_approval", "draft"):
            pre_storage[code] = pre_storage.get(code, 0) + qty

    rows = []
    for l in lines:
        su = storage_units.get(l.line_code, 0)
        ps = pre_storage.get(l.line_code, 0)
        remaining = l.storage_capacity - su - ps
        rows.append({
            "factory_code": l.factory_code,
            "factory_name": factory_names.get(l.factory_code, l.factory_code),
            "line_code": l.line_code,
            "line_name": l.line_name,
            "line_type": l.line_type,
            "storage_capacity": l.storage_capacity,
            "storage_units": su,
            "pre_storage": ps,
            "remaining": remaining,
            "status": "风险" if remaining < 0 else "正常",
        })
    return rows


@router.put("/capacity")
def update_capacity(body: CapacityIn, db: Session = Depends(get_db)):
    """手工设置某产线的总容纳数量"""
    line = db.query(ProductionLine).filter(
        ProductionLine.line_code == body.line_code).first()
    if not line:
        raise HTTPException(404, f"产线 {body.line_code} 不存在")
    line.storage_capacity = max(0, body.storage_capacity)
    db.commit()
    return {"ok": True}