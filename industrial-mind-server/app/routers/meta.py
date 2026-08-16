"""元数据接口：工厂/产线/箱型/物料"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import BoxType, Factory, Material, ProductionLine

router = APIRouter(prefix="/meta", tags=["meta"])


@router.get("/factories")
def list_factories(db: Session = Depends(get_db)):
    factories = db.query(Factory).all()
    lines = db.query(ProductionLine).all()
    return [{
        "factory_code": f.factory_code, "factory_name": f.factory_name,
        "lines": [{"line_code": l.line_code, "line_name": l.line_name,
                   "line_type": l.line_type, "daily_teu_capacity": l.daily_teu_capacity}
                  for l in lines if l.factory_code == f.factory_code],
    } for f in factories]


@router.get("/lines")
def list_lines(db: Session = Depends(get_db)):
    """产线列表（来源于 production_line 配置表）"""
    return [{
        "line_code": l.line_code, "line_name": l.line_name,
        "factory_code": l.factory_code, "line_type": l.line_type,
        "daily_teu_capacity": l.daily_teu_capacity,
    } for l in db.query(ProductionLine).order_by(ProductionLine.id).all()]


@router.get("/box-types")
def list_box_types(db: Session = Depends(get_db)):
    return [{
        "code": b.code, "name": b.name, "category": b.category,
        "daily_capacity_min": b.daily_capacity_min, "daily_capacity_max": b.daily_capacity_max,
        "daily_capacity_std": b.daily_capacity_std,
        "teu_factor": float(b.teu_factor), "cteu_factor": float(b.cteu_factor),
    } for b in db.query(BoxType).order_by(BoxType.id).all()]


@router.get("/materials")
def list_materials(db: Session = Depends(get_db)):
    return [{
        "code": m.code, "name": m.name, "category": m.category, "stock_note": m.stock_note,
        "support_units": m.support_units, "in_transit_units": m.in_transit_units,
        "arrival_date": m.arrival_date.isoformat() if m.arrival_date else None,
        "status": m.status,
    } for m in db.query(Material).all()]
