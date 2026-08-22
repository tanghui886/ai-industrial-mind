"""子 Agent：堆存风险 Storage —— 按产线统计堆存（总容纳 - 堆存 - 预堆存，<0 即爆仓风险）。
langchain 仅在 make_storage_agent() 内按需导入。
"""
from __future__ import annotations

import json

from ..database import SessionLocal
from ..models import ProductionLine, SchedulePlan

SYSTEM_PROMPT = """你是集装箱制造企业的「堆存风险 Agent」。负责按产线评估堆存风险：
堆存=已确认工令数量合计；预堆存=待审批+草稿工令数量合计；
剩余空间=总容纳-堆存-预堆存；<0 标记「风险」（爆仓），≥0 标记「正常」。
规则约束：
- 必须调用 analyze_storage 获取真实数据，指出最紧张的产线并给出建议。"""


def _db_result(data) -> str:
    return json.dumps(data, ensure_ascii=False, default=str)


def _analyze_storage() -> str:
    """堆存风险分析：按产线统计总容纳/堆存/预堆存/剩余空间，标出存在爆仓风险的产线。"""  # noqa: E501
    db = SessionLocal()
    try:
        lines = db.query(ProductionLine).order_by(ProductionLine.factory_code, ProductionLine.id).all()
        storage: dict[str, int] = {}
        pre: dict[str, int] = {}
        for code, qty, status in db.query(SchedulePlan.line_code, SchedulePlan.quantity,
                                          SchedulePlan.status).all():
            if status == "confirmed":
                storage[code] = storage.get(code, 0) + qty
            elif status in ("pending_approval", "draft"):
                pre[code] = pre.get(code, 0) + qty
        rows = []
        for l in lines:
            remaining = (l.storage_capacity - storage.get(l.line_code, 0) - pre.get(l.line_code, 0))
            rows.append({"line_code": l.line_code, "line_name": l.line_name,
                         "factory_code": l.factory_code, "capacity": l.storage_capacity,
                         "storage_units": storage.get(l.line_code, 0),
                         "pre_storage": pre.get(l.line_code, 0), "remaining": remaining,
                         "status": "风险" if remaining < 0 else "正常"})
        risks = [r for r in rows if r["status"] == "风险"]
        return _db_result({"lines": rows, "risk_count": len(risks),
                           "summary": (f"共 {len(risks)} 条产线存在爆仓风险" if risks
                                       else "各产线堆存均在安全范围内")})
    finally:
        db.close()


def make_storage_agent() -> dict:
    """构建规范化的子 Agent 配置。langchain 按需导入。"""
    from langchain.tools import tool
    return {
        "name": "storage",
        "description": "堆存风险：按产线统计堆存与剩余空间，标出爆仓风险产线。",
        "system_prompt": SYSTEM_PROMPT,
        "tools": [tool(_analyze_storage)],
    }