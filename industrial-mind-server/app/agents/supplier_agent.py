"""子 Agent：供货商动态 Supplier —— 供 Agent 查询供货商未来月度物料可用供货情况。

用于接单评估与排产预测：在接单/排产前先确认关键物料（钢材/油漆/木地板等）在未来
数月的可到货数量与日期，规避因缺料导致的交付风险。
langchain 仅在 make_supplier_agent() 内按需导入。
"""
from __future__ import annotations

import json

from ..services.supplier_dynamics import build_supplier_availability

SYSTEM_PROMPT = """你是集装箱制造企业的「供货商动态 Agent」。负责查询 5 家供货商未来数月的物料可用供货情况：
物料种类 / 可用数量 / 可到货日期，用于接单评估与排产预测。

规则约束：
- 必须调用 query_supplier_availability 获取真实 mock 数据后再回答，不要编造数量与到货日期。
- 结合供货紧张度（充足/紧张/缺货）判断关键物料是否支撑接单与排产，必要时提示提前锁单或调整排产。
- 直接给结论：可用物料、数量、可到货日期、风险点及建议。"""


def _db_result(data) -> str:
    return json.dumps(data, ensure_ascii=False, default=str)


def _query_supplier_availability(supplier: str | None = None,
                                 material_code: str | None = None,
                                 months: int = 3) -> str:
    """查询供货商物料供货能力：给定供货商编码（如 BSG/HESG/RZIS/NIPON/CIMC-TC）、物料编码（如 STEEL-HR/PAINT-PU/FLOOR-BAM）与月数，返回各月可用量、承诺量、可到货日期与紧张度。缺省查询全部供货商。"""  # noqa: E501
    return _db_result(build_supplier_availability(supplier, material_code, months))


def make_supplier_agent() -> dict:
    """构建规范化的子 Agent 配置。langchain 按需导入。"""
    from langchain.tools import tool
    return {
        "name": "supplier",
        "description": "供货商动态：查询 5 家供货商未来数月各物料可用供货（种类/数量/可到货日期/紧张度），辅助接单与排产预测。",
        "system_prompt": SYSTEM_PROMPT,
        "tools": [tool(_query_supplier_availability)],
    }