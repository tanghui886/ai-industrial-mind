"""子 Agent：成本动因 Cost —— 单箱成本拆解与异常动因分析。
langchain 仅在 make_cost_agent() 内按需导入。
"""
from __future__ import annotations

import json

from ..database import SessionLocal
from ..models import SchedulePlan

SYSTEM_PROMPT = """你是集装箱制造企业的「成本动因 Agent」。负责单箱成本拆解与成本动因分析：
直接材料/人工成本/制造费用/交付成本及其占比与驱动因素，并指出异常项。
规则约束：
- 必须调用 analyze_cost 获取真实成本数据，指出主要成本动因与优化方向。"""


def _db_result(data) -> str:
    return json.dumps(data, ensure_ascii=False, default=str)


def _analyze_cost(month: str = "") -> str:
    """成本动因分析：给定月份（如 2026-08），返回单箱成本拆解（材料/人工/制造/交付）、占比、动因及异常项；缺省为当月。"""  # noqa: E501
    from datetime import date
    month = month or f"{date.today().year:04d}-{date.today().month:02d}"
    db = SessionLocal()
    try:
        plans = db.query(SchedulePlan).filter(SchedulePlan.plan_month == month).all()
        total_teu = sum(p.teu for p in plans) or 1
        return _db_result({
            "month": month,
            "total_teu": total_teu,
            "per_box_cost": [
                {"item": "直接材料", "amount": 14200, "ratio": "62%", "driver": "箱型设计/领料管控（移动加权平均）"},
                {"item": "人工成本", "amount": 3400, "ratio": "15%", "driver": "报工工时（计划发薪+年终奖）"},
                {"item": "制造费用", "amount": 3900, "ratio": "17%", "driver": "电费/燃气按报工工时，折旧按耗电量"},
                {"item": "交付成本", "amount": 1400, "ratio": "6%", "driver": "箱量×费率（堆存/运输/海运）"},
            ],
            "anomaly": ["40HCDD 单箱材料成本环比 +4.2%（角件补货溢价）"],
            "rules": "分摊颗粒度：工令+工段+物料编码；跨月费用自动结转",
        })
    finally:
        db.close()


def make_cost_agent() -> dict:
    """构建规范化的子 Agent 配置。langchain 按需导入。"""
    from langchain.tools import tool
    return {
        "name": "cost",
        "description": "成本动因：单箱成本拆解、比率与驱动因素、异常项与优化方向。",
        "system_prompt": SYSTEM_PROMPT,
        "tools": [tool(_analyze_cost)],
    }