"""供货商动态服务：生成 5 家供货商未来 3 个月各物料的可用供货数据（Mock）。

数据为确定性生成（基于供应商 × 月份偏移 + 物料播种量），保证接口与 Agent 调用结果稳定可控，
便于接单评估与排产预测。数据可按供应商 / 物料 / 月份过滤。
"""
from __future__ import annotations

from datetime import date

# 供货商定义
SUPPLIERS: list[dict] = [
    {"code": "BSG", "name": "宝武钢铁集团", "factory": "SHPD", "port": "启东港", "category": ["钢材"]},
    {"code": "HESG", "name": "河钢集团", "factory": "SHPD", "port": "青岛港", "category": ["钢材"]},
    {"code": "RZIS", "name": "日照钢铁", "factory": "SHBS", "port": "青岛港", "category": ["钢材", "波纹板"]},
    {"code": "NIPON", "name": "立邦涂料（中国）", "factory": "SHBS", "port": "上海港", "category": ["油漆"]},
    {"code": "CIMC-TC", "name": "中集同创木业", "factory": "SHJS", "port": "上海港", "category": ["木制品"]},
]

# 物料定义
MATERIALS: list[dict] = [
    {"code": "STEEL-HR", "name": "热轧卷板", "category": "钢材", "unit": "吨"},
    {"code": "STEEL-ECO", "name": "耐候钢", "category": "钢材", "unit": "吨"},
    {"code": "WWD", "name": "波纹板", "category": "钢材", "unit": "张"},
    {"code": "CORNER", "name": "角件", "category": "紧固件", "unit": "套"},
    {"code": "PAINT-PU", "name": "聚氨酯面漆", "category": "油漆", "unit": "桶"},
    {"code": "PAINT-PRM", "name": "环氧底漆", "category": "油漆", "unit": "桶"},
    {"code": "FLOOR-BAM", "name": "竹木地板", "category": "木制品", "unit": "套"},
]

# 供应商可供货物料及基准月供货量（确定性种子：随月份小幅波动）
_SUPPLIER_SUPPLY: dict[str, list[tuple[str, int, int]]] = {
    "BSG": [("STEEL-HR", 1800, 8), ("STEEL-ECO", 900, 10), ("CORNER", 1500, 6)],
    "HESG": [("STEEL-ECO", 1200, 9), ("STEEL-HR", 1400, 7)],
    "RZIS": [("STEEL-HR", 1000, 10), ("WWD", 3200, 8), ("CORNER", 900, 5)],
    "NIPON": [("PAINT-PU", 600, 5), ("PAINT-PRM", 700, 5)],
    "CIMC-TC": [("FLOOR-BAM", 2400, 12)],
}


def _next_months(n: int = 3, base: date | None = None) -> list[tuple[int, int]]:
    base = base or date.today()
    y, m = base.year, base.month
    res: list[tuple[int, int]] = []
    for _ in range(n):
        res.append((y, m))
        m += 1
        if m > 12:
            m, y = 1, y + 1
    return res


def _availability_quality(supplier_idx: int, month_idx: int, mat_idx: int, avail: int) -> str:
    """确定性供需紧张度：基于月份/物料偏移判定，便于 Agent 用于排产预判。"""
    score = (supplier_idx * 3 + month_idx * 2 + mat_idx) % 5
    if avail <= 0:
        return "缺货"
    if score in (0, 1):
        return "紧张"
    return "充足"


def build_supplier_availability(supplier_code: str | None = None,
                                material_code: str | None = None,
                                months: int = 3,
                                today: date | None = None) -> dict:
    """返回供货商可用供货日历。

    结构：
    {
      "generated_at": "YYYY-MM-DD",
      "months": ["2026-09", "2026-10", "2026-11"],
      "suppliers": [{"code","name","factory","port"}],
      "items": [{
          "supplier_code","supplier": 名称,
          "month": "2026-09",
          "material_code","material": 名称,"category","unit",
          "committed_qty": 承诺量, "available_qty": 可用量,
          "arrival_date": 可到货日期, "status": 充足/紧张/缺货
      }]
    }
    """
    today = today or date.today()
    months_list = _next_months(months, today)
    month_keys = [f"{y:04d}-{m:02d}" for y, m in months_list]

    suppliers = [s for s in SUPPLIERS if not supplier_code or s["code"] == supplier_code]
    items: list[dict] = []
    mat_index = {m["code"]: i for i, m in enumerate(MATERIALS)}
    for mi, (y, m) in enumerate(months_list):
        for si, sup in enumerate(suppliers):
            for mat_code, base_qty, lead_days in _SUPPLIER_SUPPLY.get(sup["code"], []):
                if material_code and mat_code != material_code:
                    continue
                mat = next((x for x in MATERIALS if x["code"] == mat_code), None)
                if not mat:
                    continue
                # 确定性波动：±15%
                delta = (si * 7 + mi * 5 + mat_index.get(mat_code, 0) * 3) % 30 - 15
                available = max(0, int(base_qty * (100 + delta) / 100))
                day = ((si * 3 + mi * 5 + lead_days) % 26) + 2
                arrival = date(y, m, day)
                status = _availability_quality(si, mi, mat_index.get(mat_code, 0), available)
                items.append({
                    "supplier_code": sup["code"],
                    "supplier": sup["name"],
                    "month": f"{y:04d}-{m:02d}",
                    "material_code": mat_code,
                    "material": mat["name"],
                    "category": mat["category"],
                    "unit": mat["unit"],
                    "committed_qty": base_qty,
                    "available_qty": available,
                    "arrival_date": arrival.isoformat(),
                    "status": status,
                    "port": sup["port"],
                    "lead_days": lead_days,
                })
    return {
        "generated_at": today.isoformat(),
        "months": month_keys,
        "suppliers": [{"code": s["code"], "name": s["name"], "factory": s["factory"],
                       "port": s["port"]} for s in suppliers],
        "items": items,
    }