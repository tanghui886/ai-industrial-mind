"""子 Agent：物料缺口 Material —— 按工厂/产线统计物料缺口（在库 - 订单扣减 - 草稿 < 0）。
langchain 仅在 make_material_agent() 内按需导入。
"""
from __future__ import annotations

import json

from ..database import SessionLocal
from ..services.material_usage import material_usage_by_status
from ..models import Material

SYSTEM_PROMPT = """你是集装箱制造企业的「物料缺口 Agent」。负责统计各物料是否存在缺口：
缺口 = 在库总量 - 订单扣减（审批中工令用量）- 草稿工令用量；<0 记为缺口。
规则约束：
- 必须调用 analyze_material_gap 获取真实数据并按缺口量从大到小给出补货建议。
- 可直接判断物料状态：缺口>0 →「需补货」，缺口=0 →「充足」。"""


def _db_result(data) -> str:
    return json.dumps(data, ensure_ascii=False, default=str)


def _analyze_material_gap(factory: str | None = None) -> str:
    """物料缺口分析：按工厂统计各物料在库/订单扣减/缺口量及补货建议；未指定工厂则统计全部。"""  # noqa: E501
    db = SessionLocal()
    try:
        rows = []
        for m in db.query(Material).order_by(Material.factory, Material.id).all():
            if factory and m.factory != factory:
                continue
            order_deducted = material_usage_by_status(db, m, ["pending_approval"])
            draft_usage = material_usage_by_status(db, m, ["draft"])
            remainder = m.in_stock_units - order_deducted - draft_usage
            gap = 0 if remainder > 0 else abs(remainder)
            rows.append({"material": m.name, "code": m.code, "unit": m.unit, "factory": m.factory,
                         "in_stock": m.in_stock_units, "order_deducted": round(order_deducted),
                         "gap": round(gap), "status": "需补货" if gap > 0 else "充足",
                         "action": "建议锁定在途订单并评估受影响工令排产调整" if gap > 0 else "库存充足，无需补货"})
        gaps = [r for r in rows if r["gap"] > 0]
        return _db_result({"factory": factory or "全部", "gaps": rows,
                           "summary": f"共 {len(gaps)} 项物料需补货"})
    finally:
        db.close()


def make_material_agent() -> dict:
    """构建规范化的子 Agent 配置。langchain 按需导入。"""
    from langchain.tools import tool
    return {
        "name": "material",
        "description": "物料缺口：统计各物料在库/订单扣减/缺口量及补货建议。",
        "system_prompt": SYSTEM_PROMPT,
        "tools": [tool(_analyze_material_gap)],
    }