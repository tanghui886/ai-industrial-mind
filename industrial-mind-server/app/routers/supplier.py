"""供货商动态接口：mock 5 家供货商未来 3 个月各物料的可用供货情况。

供前端「供货商动态」页面与 Agent（工具接口）查询，辅助接单与排产预测。
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Query

from ..services.supplier_dynamics import MATERIALS, SUPPLIERS, build_supplier_availability

router = APIRouter(prefix="/supplier", tags=["supplier"])


@router.get("/availability")
def supplier_availability(supplier: str | None = Query(default=None, description="供货商编码，如 BSG"),
                          material: str | None = Query(default=None, description="物料编码，如 STEEL-HR"),
                          months: int = Query(default=3, ge=1, le=12)):
    """查询供货商未来 N 个月的物料可用供货（种类/数量/可到货日期），可按供货商、物料过滤。"""
    return build_supplier_availability(supplier, material, months)


@router.get("/options")
def supplier_options():
    """供货商与物料选项（供页面筛选用）。"""
    return {
        "suppliers": SUPPLIERS,
        "materials": MATERIALS,
        "months": build_supplier_availability(months=3).get("months", []),
    }