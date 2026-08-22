"""物料维护接口：物料（原材料/关键物料）的增删改查（仅具备 material.manage 权限者操作）"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Material
from ..permissions import require_perm
from ..services.material_usage import material_usage_by_status

router = APIRouter(prefix="/material", tags=["material"])


def _stock_fields(db: Session, m: Material) -> tuple[int, int]:
    """动态计算物料的「订单扣减」与「缺口」：
    - 订单扣减 = 该物料所属工厂所有「审批中」工令的用量总和
    - 缺口 = |在库总量 - 订单扣减 - 草稿工令用量|，若该差值 > 0 则为 0
    """
    order_deducted = material_usage_by_status(db, m, ["pending_approval"])
    draft_usage = material_usage_by_status(db, m, ["draft"])
    remainder = m.in_stock_units - order_deducted - draft_usage
    gap = 0 if remainder > 0 else abs(remainder)
    return round(order_deducted), round(gap)


class MaterialIn(BaseModel):
    code: str
    name: str
    category: str
    factory: str = "SHPD"
    unit: str = ""
    stock_note: str = ""
    in_stock_units: int = 0
    order_deducted_units: int = 0
    gap_units: int = 0
    support_units: int = 0
    in_transit_units: int = 0
    purchase_units: int = 0
    arrival_date: date | None = None
    status: str = "充足"


def _material_dict(m: Material) -> dict:
    return {
        "id": m.id, "code": m.code, "name": m.name, "category": m.category,
        "factory": m.factory, "unit": m.unit, "stock_note": m.stock_note,
        "in_stock_units": m.in_stock_units,
        "order_deducted_units": m.order_deducted_units,
        "gap_units": m.gap_units,
        "support_units": m.support_units,
        "in_transit_units": m.in_transit_units,
        "purchase_units": m.purchase_units,
        "arrival_date": m.arrival_date.isoformat() if m.arrival_date else None,
        "status": m.status,
    }


@router.get("/stats")
def material_stats(_: str = Depends(require_perm("material.manage")),
                   db: Session = Depends(get_db)):
    """物料数量统计：按工厂汇总在库/在途/采购/扣减/转换台数（扣减为动态计算）"""
    rows = db.query(Material).all()
    by_factory: dict[str, dict] = {}
    total = {"in_stock_units": 0, "in_transit_units": 0, "purchase_units": 0,
             "order_deducted_units": 0, "support_units": 0}
    for m in rows:
        order_deducted, _ = _stock_fields(db, m)
        f = by_factory.setdefault(m.factory, {
            "factory": m.factory, "in_stock_units": 0, "in_transit_units": 0,
            "purchase_units": 0, "order_deducted_units": 0, "support_units": 0,
            "material_count": 0})
        f["in_stock_units"] += m.in_stock_units
        f["in_transit_units"] += m.in_transit_units
        f["purchase_units"] += m.purchase_units
        f["order_deducted_units"] += order_deducted
        f["support_units"] += m.support_units
        f["material_count"] += 1
        total["in_stock_units"] += m.in_stock_units
        total["in_transit_units"] += m.in_transit_units
        total["purchase_units"] += m.purchase_units
        total["order_deducted_units"] += order_deducted
        total["support_units"] += m.support_units
    return {"total": total, "by_factory": list(by_factory.values())}


@router.get("/list")
def list_materials(_: str = Depends(require_perm("material.manage")),
                   db: Session = Depends(get_db)):
    rows = []
    for m in db.query(Material).order_by(Material.id).all():
        d = _material_dict(m)
        d["order_deducted_units"], d["gap_units"] = _stock_fields(db, m)
        # 状态按缺口自动填充：缺口 0 → 充足，有缺口 → 需补货
        d["status"] = "需补货" if d["gap_units"] > 0 else "充足"
        rows.append(d)
    return rows


@router.post("/")
def create_material(body: MaterialIn, _: str = Depends(require_perm("material.manage")),
                    db: Session = Depends(get_db)):
    code = body.code.strip()
    if not code or not body.name.strip():
        raise HTTPException(400, "物料编码与名称不能为空")
    if db.query(Material).filter(Material.code == code).first():
        raise HTTPException(400, f"物料编码「{code}」已存在")
    db.add(Material(code=code, name=body.name.strip(), category=body.category.strip(),
                    factory=body.factory.strip() or "SHPD", unit=body.unit.strip(),
                    stock_note=body.stock_note.strip(),
                    in_stock_units=body.in_stock_units,
                    order_deducted_units=body.order_deducted_units,
                    gap_units=body.gap_units,
                    support_units=body.support_units,
                    in_transit_units=body.in_transit_units,
                    purchase_units=body.purchase_units,
                    arrival_date=body.arrival_date,
                    status=body.status or "充足"))
    db.commit()
    return {"ok": True, "message": f"物料「{body.name.strip()}」已创建"}


@router.put("/{material_id}")
def update_material(material_id: int, body: MaterialIn,
                    _: str = Depends(require_perm("material.manage")),
                    db: Session = Depends(get_db)):
    m = db.query(Material).filter(Material.id == material_id).first()
    if not m:
        raise HTTPException(404, "物料不存在")
    if not body.code.strip() or not body.name.strip():
        raise HTTPException(400, "物料编码与名称不能为空")
    dup = db.query(Material).filter(Material.code == body.code.strip(),
                                    Material.id != material_id).first()
    if dup:
        raise HTTPException(400, f"物料编码「{body.code.strip()}」已存在")
    m.code = body.code.strip()
    m.name = body.name.strip()
    m.category = body.category.strip()
    m.factory = body.factory.strip() or "SHPD"
    m.unit = body.unit.strip()
    m.stock_note = body.stock_note.strip()
    m.in_stock_units = body.in_stock_units
    m.order_deducted_units = body.order_deducted_units
    m.gap_units = body.gap_units
    m.support_units = body.support_units
    m.in_transit_units = body.in_transit_units
    m.purchase_units = body.purchase_units
    m.arrival_date = body.arrival_date
    m.status = body.status or "充足"
    db.commit()
    return {"ok": True, "message": f"物料「{m.name}」已更新"}


@router.delete("/{material_id}")
def delete_material(material_id: int, _: str = Depends(require_perm("material.manage")),
                    db: Session = Depends(get_db)):
    m = db.query(Material).filter(Material.id == material_id).first()
    if not m:
        raise HTTPException(404, "物料不存在")
    db.delete(m)
    db.commit()
    return {"ok": True, "message": f"物料「{m.name}」已删除"}