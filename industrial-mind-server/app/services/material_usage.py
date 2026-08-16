"""物料用量计算：按工令箱型/数量估算各物料用量（无独立 BOM，复用物料齐套消耗逻辑）

该模块是「物料维护 - 订单扣减/缺口」与「成本 - 物料明细」共用的用量口径：
一个工令在某工厂下消耗各物料的数量，由工令箱型的 TEU 系数与数量估算得出。
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from ..models import BoxType, Material, SchedulePlan


def consume_units(base: str, quantity: int, teu_factor: float) -> float:
    """按物料类型主代码估算单个工令的物料用量

    - STEEL  钢板：按数量 × TEU 系数
    - PAINT  涂料：按数量 × TEU 系数 × 0.9
    - FLOOR  木地板：按数量 × TEU 系数 × 0.8
    - CORNER 角件 / LOCK 五金：按台数（1 台配 1 套）
    - 其他：按数量
    """
    if base in ("STEEL",):
        return quantity * teu_factor
    if base == "PAINT":
        return quantity * teu_factor * 0.9
    if base == "FLOOR":
        return quantity * teu_factor * 0.8
    if base in ("CORNER", "LOCK"):
        return float(quantity)
    return float(quantity)


def _teu_map(db: Session) -> dict[str, float]:
    return {b.code: float(b.teu_factor) for b in db.query(BoxType).all()}


def work_order_usages(db: Session) -> list[dict]:
    """生成「产线 × 工令 × 物料」用量明细（来源：schedule_plan + box_type + material）"""
    teu_map = _teu_map(db)
    materials = db.query(Material).all()
    # 按 工厂+物料主代码 建立映射，避免每个工令重复查库
    mat_by_factory_base: dict[tuple[str, str], Material] = {}
    for m in materials:
        mat_by_factory_base[(m.factory, m.code.split("-")[0])] = m

    plans = (db.query(SchedulePlan)
             .order_by(SchedulePlan.line_code, SchedulePlan.work_order_no).all())
    rows: list[dict] = []
    for p in plans:
        teu = teu_map.get(p.box_type, 1.0)
        for (factory, base), m in mat_by_factory_base.items():
            if factory != p.factory_code:
                continue
            rows.append({
                "work_order_no": p.work_order_no,
                "line_code": p.line_code,
                "factory_code": p.factory_code,
                "box_type": p.box_type,
                "quantity": p.quantity,
                "status": p.status,
                "material_code": m.code,
                "material_name": m.name,
                "unit": m.unit,
                "usage_units": round(consume_units(base, p.quantity, teu), 1),
            })
    return rows


def material_usage_by_status(db: Session, material: Material,
                             statuses: list[str]) -> float:
    """某物料在其所属工厂下、指定状态工令的用量总和"""
    teu_map = _teu_map(db)
    base = material.code.split("-")[0]
    plans = (db.query(SchedulePlan)
             .filter(SchedulePlan.factory_code == material.factory,
                     SchedulePlan.status.in_(statuses)).all())
    total = 0.0
    for p in plans:
        teu = teu_map.get(p.box_type, 1.0)
        total += consume_units(base, p.quantity, teu)
    return total