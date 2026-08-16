"""成本动因大屏 + 成本动因各维度数据管理接口（mock 示例数据，按成本动因.md 结构）"""
from __future__ import annotations

import random
import zlib
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import CostAnalysis, CostBaseline, Material, ProductionLine, SchedulePlan
from ..services.llm import chat_completion
from ..services.material_usage import work_order_usages

router = APIRouter(prefix="/cost", tags=["cost"])

# 成本动因维度（对应 成本动因.md 的业务场景）
DIMENSIONS = ["采购", "直接材料", "人工成本", "制造费用", "交付成本"]

# 工令号维度下的成本构成项（与 DIMENSIONS 一致，用于每个工令的明细拆解）
WORK_ORDER_DIMENSIONS = ["采购", "直接材料", "人工成本", "制造费用", "交付成本"]

# 各维度下的场景细分与成本动因（来自 成本动因.md）
# (dimension, scene, driver, unit)
DRIVER_SCHEMA = [
    ("采购", "材料采购", "采购订单量", "吨"),
    ("采购", "材料采购", "铁矿石市场价格", "元/吨"),
    ("采购", "材料采购", "焦煤市场价格", "元/吨"),
    ("采购", "材料采购", "供应商集中度", "%"),
    ("直接材料", "工令领料", "物料单价（移动加权平均）", "元/单位"),
    ("直接材料", "工令领料", "耗用量（领用-退库）", "单位"),
    ("直接材料", "形态转换", "箱型设计技术规范", "元/箱"),
    ("直接材料", "废料冲减", "废料回收利用率", "%"),
    ("人工成本", "计划发薪", "报工工时", "小时"),
    ("人工成本", "年终奖", "工人熟练度", "元/小时"),
    ("人工成本", "直接/间接用工", "班组定编", "人"),
    ("制造费用", "能源费用-电费", "用电量", "kWh"),
    ("制造费用", "能源费用-水费", "用水量", "t"),
    ("制造费用", "能源费用-燃气费", "燃气用量", "m³"),
    ("制造费用", "一次性领料", "五金/环保/劳保领用量", "元"),
    ("制造费用", "折旧与租赁", "耗电量占比", "%"),
    ("交付成本", "堆存费", "预估堆存天数", "天"),
    ("交付成本", "运输费", "运输箱量", "箱"),
    ("交付成本", "拖车/海运", "单箱费率", "元/箱"),
]


def _gen_driver_rows(db: Session) -> list[dict]:
    """按 production_line 产线 + schedule_plan 工令号生成固定 mock 维度明细（确定性随机）"""
    random.seed(8)
    lines = {l.line_code: l.line_name for l in db.query(ProductionLine).all()}
    plans = db.query(SchedulePlan).filter(SchedulePlan.plan_month == "2026-08").order_by(
        SchedulePlan.work_order_no).all()
    rows: list[dict] = []
    sid = 1
    for p in plans:
        for dim, scene, driver, unit in DRIVER_SCHEMA:
            rows.append({
                "id": sid,
                "line_code": p.line_code,
                "line_name": lines.get(p.line_code, p.line_code),
                "work_order_no": p.work_order_no,
                "dimension": dim, "scene": scene, "driver": driver, "unit": unit,
                "period": p.plan_month,
                "value": round(random.uniform(60, 420), 1),
                "cost": random.randint(8, 90) * 10000,
                "note": random.choice(["平稳", "环比上升", "环比下降", "需关注"]),
            })
            sid += 1
    return rows


def _shift_month(d: date, offset: int) -> tuple[int, int]:
    total = d.year * 12 + (d.month - 1) + offset
    return total // 12, total % 12 + 1


_driver_rows: list[dict] | None = None
_next_id = 1


def _ensure_rows(db: Session) -> list[dict]:
    """惰性初始化维度明细数据（首次访问时基于 db 生成，后续复用支持 CRUD）"""
    global _driver_rows, _next_id
    if _driver_rows is None:
        _driver_rows = _gen_driver_rows(db)
        _next_id = len(_driver_rows) + 1
    return _driver_rows


@router.get("/screen")
def cost_screen(line_code: str | None = None, work_order_no: str | None = None,
                db: Session = Depends(get_db)):
    """成本动因大屏聚合数据（支持按产线 / 工令号维度筛选）"""
    # 单箱成本构成（元，来自 成本动因.md per_box 结构）
    per_box = [
        {"item": "直接材料", "amount": 14200, "ratio": "62%", "driver": "物料单价×耗用量（移动加权平均）"},
        {"item": "人工成本", "amount": 3400, "ratio": "15%", "driver": "报工工时（计划发薪+年终奖）"},
        {"item": "制造费用", "amount": 3900, "ratio": "17%", "driver": "电/燃气按报工工时，折旧按耗电量"},
        {"item": "交付成本", "amount": 1400, "ratio": "6%", "driver": "箱量×费率（堆存/运输/海运）"},
    ]
    total = sum(c["amount"] for c in per_box)

    # 各维度成本月度趋势（随产线/工令号筛选变化，确定性随机）
    seed_key = work_order_no or line_code or "all"
    random.seed(zlib.crc32(seed_key.encode()))
    base = {"采购": 1000, "直接材料": 6200, "人工成本": 1500, "制造费用": 1700, "交付成本": 600}
    labels = []
    series = {d: [] for d in DIMENSIONS}
    for m_offset in range(6, -1, -1):
        year, month = _shift_month(date(2026, 8, 1), -m_offset)
        labels.append(f"{year}-{month:02d}")
        for dim in DIMENSIONS:
            series[dim].append(round(base[dim] * random.uniform(0.9, 1.15)))

    # 主要成本动因影响度（Top 动因）
    drivers = [
        {"name": "铁矿石市场价格", "impact": 18.2, "dimension": "采购", "trend": "up"},
        {"name": "物料单价（移动加权平均）", "impact": 15.6, "dimension": "直接材料", "trend": "up"},
        {"name": "报工工时", "impact": 12.4, "dimension": "人工成本", "trend": "flat"},
        {"name": "用电量", "impact": 9.8, "dimension": "制造费用", "trend": "down"},
        {"name": "废料回收利用率", "impact": 7.3, "dimension": "直接材料", "trend": "flat"},
        {"name": "运输箱量", "impact": 5.1, "dimension": "交付成本", "trend": "up"},
    ]

    # 成本异常（随筛选范围标注）
    scope = work_order_no or line_code or "全厂"
    anomalies = [
        {"level": "高", "desc": f"{scope}：40HCDD 单箱材料成本环比 +4.2%（角件补货溢价）"},
        {"level": "中", "desc": f"{scope}：电费动因环比 +6.1%，8号变压器无线损采集"},
        {"level": "中", "desc": f"{scope}：人工报工时薪环比 +2.8%，熟练度下降"},
        {"level": "低", "desc": f"{scope}：堆存费预提率波动，费率口径待标准化"},
    ]

    return {"per_box": per_box, "total": total, "labels": labels,
            "series": series, "drivers": drivers, "anomalies": anomalies}


@router.get("/options")
def cost_options(db: Session = Depends(get_db)):
    """成本大屏/管理筛选下拉：产线（production_line）+ 工令号（schedule_plan）+ 客户 + 箱型 + 物料"""
    lines = [{"line_code": l.line_code, "line_name": l.line_name}
             for l in db.query(ProductionLine).order_by(ProductionLine.id).all()]
    work_orders = [w[0] for w in db.query(SchedulePlan.work_order_no).filter(
        SchedulePlan.plan_month == "2026-08").distinct().order_by(SchedulePlan.work_order_no).all()]
    customers = sorted({c[0] for c in db.query(SchedulePlan.customer).distinct().all() if c[0]})
    box_types = [b[0] for b in db.query(SchedulePlan.box_type).distinct().order_by(SchedulePlan.box_type).all()]
    materials = [{"code": m.code, "name": m.name, "factory": m.factory, "unit": m.unit}
                 for m in db.query(Material).order_by(Material.id).all()]
    return {"lines": lines, "work_orders": work_orders, "customers": customers,
            "box_types": box_types, "materials": materials}


@router.get("/material-details")
def list_material_details(line_code: str | None = None,
                          work_order_no: str | None = None,
                          material_code: str | None = None,
                          db: Session = Depends(get_db)):
    """物料明细：按产线、工令展示每个工令的物料用量（material_usage 口径）"""
    line_names = {l.line_code: l.line_name for l in db.query(ProductionLine).all()}
    rows = work_order_usages(db)
    if line_code:
        rows = [r for r in rows if r["line_code"] == line_code]
    if work_order_no:
        rows = [r for r in rows if r["work_order_no"] == work_order_no]
    if material_code:
        rows = [r for r in rows if r["material_code"] == material_code]
    for r in rows:
        r["line_name"] = line_names.get(r["line_code"], r["line_code"])
    return rows


@router.get("/drivers")
def list_drivers(dimension: str | None = None, period: str | None = None,
                 line_code: str | None = None, work_order_no: str | None = None,
                 db: Session = Depends(get_db)):
    """成本动因各维度数据明细列表（支持按维度/期间/产线/工令号过滤）"""
    rows = _ensure_rows(db)
    if dimension:
        rows = [r for r in rows if r["dimension"] == dimension]
    if period:
        rows = [r for r in rows if r["period"] == period]
    if line_code:
        rows = [r for r in rows if r["line_code"] == line_code]
    if work_order_no:
        rows = [r for r in rows if r["work_order_no"] == work_order_no]
    return rows


@router.get("/work-orders")
def list_work_orders(line_code: str | None = None, month: str = "2026-08",
                     keyword: str | None = None, db: Session = Depends(get_db)):
    """工令号维度成本明细：每个工令对应各维度成本数据（产线来源于 production_line 配置表）

    从排产工令（schedule_plan）+ 产线配置（production_line）生成确定性 mock 成本拆解。
    """
    # 产线名称映射（来源于 production_line）
    line_names = {l.line_code: l.line_name for l in db.query(ProductionLine).all()}

    plans = db.query(SchedulePlan).filter(SchedulePlan.plan_month == month).order_by(
        SchedulePlan.work_order_no).all()
    if line_code:
        plans = [p for p in plans if p.line_code == line_code]
    if keyword:
        kw = keyword.strip().lower()
        plans = [p for p in plans
                 if kw in p.work_order_no.lower() or kw in (p.customer or "").lower()
                 or kw in (p.box_type or "").lower()]

    rows = []
    for p in plans:
        # 确定性随机：同一工令每次/每次启动生成一致的各维度成本
        random.seed(zlib.crc32(p.work_order_no.encode()))
        base = 300 + p.quantity * random.randint(60, 160)
        costs = {}
        for dim in WORK_ORDER_DIMENSIONS:
            ratio = {"采购": 0.10, "直接材料": 0.62, "人工成本": 0.15,
                     "制造费用": 0.17, "交付成本": 0.06}[dim]
            costs[dim] = round(base * ratio * random.uniform(0.9, 1.1))
        costs["合计"] = sum(costs.values())
        rows.append({
            "work_order_no": p.work_order_no,
            "line_code": p.line_code,
            "line_name": line_names.get(p.line_code, p.line_code),
            "factory_code": p.factory_code,
            "box_type": p.box_type,
            "customer": p.customer,
            "quantity": p.quantity,
            "period": p.plan_month,
            "costs": costs,
        })
    return rows


class DriverIn(BaseModel):
    dimension: str
    scene: str
    driver: str
    unit: str = ""
    period: str
    value: float = 0
    cost: float = 0
    note: str = ""


@router.post("/drivers")
def create_driver(body: DriverIn, db: Session = Depends(get_db)):
    global _next_id
    if body.dimension not in DIMENSIONS:
        raise HTTPException(400, f"非法成本维度：{body.dimension}")
    rows = _ensure_rows(db)
    row = body.model_dump()
    row["id"] = _next_id
    _next_id += 1
    rows.append(row)
    return {"ok": True, "message": f"动因「{body.driver}」已新增", "id": row["id"]}


@router.put("/drivers/{driver_id}")
def update_driver(driver_id: int, body: DriverIn, db: Session = Depends(get_db)):
    rows = _ensure_rows(db)
    for r in rows:
        if r["id"] == driver_id:
            if body.dimension not in DIMENSIONS:
                raise HTTPException(400, f"非法成本维度：{body.dimension}")
            r.update(body.model_dump())
            return {"ok": True, "message": f"动因「{body.driver}」已更新"}
    raise HTTPException(404, "动因数据不存在")


@router.delete("/drivers/{driver_id}")
def delete_driver(driver_id: int, db: Session = Depends(get_db)):
    rows = _ensure_rows(db)
    for i, r in enumerate(rows):
        if r["id"] == driver_id:
            rows.pop(i)
            return {"ok": True, "message": "动因数据已删除"}
    raise HTTPException(404, "动因数据不存在")


# ===================== 成本动因基准配置 =====================

CAD_COST_SYSTEM_PROMPT = """你是集装箱制造企业的成本动因分析专家。请基于给定的「实际动因因子」与「基准动因因子」的逐项比对结果，输出一份简洁、结构化的成本动因分析报告。

要求：
- 用中文输出，使用 Markdown 列表/小标题，控制在 300 字以内。
- 分三部分：① 总体结论（成本是否超基准、主要风险维度）；② 超基准的前 3 项动因（驱动/T0 实际值 T1 基准值 T2 差异率，说明原因与影响）；③ 降本建议（针对每项给出可落地的举措）。
- 只基于给定数据，不要编造数据。"""

CAD_COST_SUMMARY_PROMPT = """你是集装箱制造企业的成本动因分析专家。请基于给定的历史「异常工令」及其超基准动因的汇总信息，输出一份「异常动因分析汇总」报告。

要求：
- 用中文输出，使用 Markdown 列表/小标题，控制在 300 字以内。
- 分三部分：① 总体结论（异常工令数量、超基准最集中的维度）；② Top 异常动因（按出现频次/平均差异率排序，说明影响面与原因）；③ 降本建议（针对高优先动因给出可落地举措）。
- 只基于给定数据，不要编造数据。"""


def _gen_factors(seed_key: str) -> list[dict]:
    """按 seed_key 生成确定性 mock 动因因子明细（与 /cost/drivers 同一套 DRIVER_SCHEMA）"""
    random.seed(zlib.crc32(seed_key.encode()))
    factors = []
    for dim, scene, driver, unit in DRIVER_SCHEMA:
        factors.append({
            "key": driver,
            "dimension": dim, "scene": scene, "driver": driver, "unit": unit,
            "value": round(random.uniform(60, 420), 1),
        })
    return factors


def _serialize_baseline(b: CostBaseline) -> dict:
    return {"id": b.id, "customer": b.customer, "box_type": b.box_type,
            "source_work_order_no": b.source_work_order_no, "remark": b.remark,
            "factors": b.factors, "updated_at": b.updated_at.isoformat() if b.updated_at else ""}


class FactorIn(BaseModel):
    key: str = ""
    dimension: str = ""
    scene: str = ""
    driver: str
    unit: str = ""
    value: float = 0


class BaselineIn(BaseModel):
    customer: str = ""
    box_type: str
    source_work_order_no: str = ""
    remark: str = ""
    factors: list[FactorIn] = Field(default_factory=list)


class AnalyzeIn(BaseModel):
    mode: str = "all"       # work_order | customer | box_type | all
    work_order_no: str = ""
    customer: str = ""
    box_type: str = ""
    force: bool = False     # 强制重新分析：清理范围内已分析记录后重算


@router.get("/baselines")
def list_baselines(customer: str | None = None, box_type: str | None = None,
                   db: Session = Depends(get_db)):
    """基准配置列表（可按客户/箱型过滤；customer 为空为「无客户」基线）"""
    q = db.query(CostBaseline)
    if customer is not None:
        q = q.filter(CostBaseline.customer == customer)
    if box_type:
        q = q.filter(CostBaseline.box_type == box_type)
    rows = q.order_by(CostBaseline.box_type, CostBaseline.customer).all()
    return [_serialize_baseline(b) for b in rows]


@router.get("/baselines/init")
def baseline_init(work_order_no: str | None = None, customer: str | None = None,
                  box_type: str | None = None, db: Session = Depends(get_db)):
    """初始化基准动因因子：
    - 选择工令：带出该工令的各动因因子明细，并回填其 客户/箱型
    - 选择客户+箱型：存在同客户基准则带出，否则用「无客户同箱型」基准，再没有则按箱型默认因子
    """
    if work_order_no:
        plan = db.query(SchedulePlan).filter(SchedulePlan.work_order_no == work_order_no).first()
        if not plan:
            raise HTTPException(404, "工令号不存在")
        factors = _gen_factors(work_order_no)
        return {"customer": plan.customer, "box_type": plan.box_type,
                "source_work_order_no": work_order_no, "factors": factors, "mode": "work_order"}
    if not box_type:
        raise HTTPException(400, "请选择箱型")
    customer = customer or ""
    # 同客户基准
    bl = (db.query(CostBaseline)
          .filter(CostBaseline.customer == customer, CostBaseline.box_type == box_type).first())
    if bl:
        return {"customer": customer, "box_type": box_type,
                "source_work_order_no": bl.source_work_order_no, "factors": bl.factors, "mode": "existing"}
    # 无客户同箱型基准兜底
    default_bl = (db.query(CostBaseline)
                  .filter(CostBaseline.customer == "", CostBaseline.box_type == box_type).first())
    if default_bl:
        return {"customer": customer, "box_type": box_type,
                "source_work_order_no": "", "factors": default_bl.factors, "mode": "default"}
    return {"customer": customer, "box_type": box_type,
            "source_work_order_no": "", "factors": _gen_factors(box_type), "mode": "default"}


@router.post("/baselines")
def create_baseline(body: BaselineIn, db: Session = Depends(get_db)):
    """新增/更新基准（按 客户+箱型 唯一，存在则更新）"""
    customer = body.customer or ""
    bl = (db.query(CostBaseline)
          .filter(CostBaseline.customer == customer, CostBaseline.box_type == body.box_type).first())
    if bl:
        bl.factors = [f.model_dump() for f in body.factors]
        bl.source_work_order_no = body.source_work_order_no
        bl.remark = body.remark
        db.commit()
        return {"ok": True, "message": f"{customer or '无客户'}/{body.box_type} 基准已更新", "id": bl.id}
    bl = CostBaseline(customer=customer, box_type=body.box_type,
                      source_work_order_no=body.source_work_order_no, remark=body.remark,
                      factors=[f.model_dump() for f in body.factors])
    db.add(bl)
    db.commit()
    return {"ok": True, "message": f"{customer or '无客户'}/{body.box_type} 基准已新增", "id": bl.id}


@router.put("/baselines/{baseline_id}")
def update_baseline(baseline_id: int, body: BaselineIn, db: Session = Depends(get_db)):
    bl = db.query(CostBaseline).filter(CostBaseline.id == baseline_id).first()
    if not bl:
        raise HTTPException(404, "基准不存在")
    bl.customer = body.customer or ""
    bl.box_type = body.box_type
    bl.source_work_order_no = body.source_work_order_no
    bl.remark = body.remark
    bl.factors = [f.model_dump() for f in body.factors]
    db.commit()
    return {"ok": True, "message": "基准已更新", "id": bl.id}


@router.delete("/baselines/{baseline_id}")
def delete_baseline(baseline_id: int, db: Session = Depends(get_db)):
    bl = db.query(CostBaseline).filter(CostBaseline.id == baseline_id).first()
    if not bl:
        raise HTTPException(404, "基准不存在")
    db.delete(bl)
    db.commit()
    return {"ok": True, "message": "基准已删除"}


def _analyze_one(plan: SchedulePlan, db: Session) -> dict:
    """对单个工令做动因基准比对：同客户同箱型 → 无客户同箱型 → 箱型默认"""
    customer, box_type = plan.customer, plan.box_type
    actual = _gen_factors(plan.work_order_no)
    baseline_kind = "同客户同箱型基准"
    bl = (db.query(CostBaseline)
          .filter(CostBaseline.customer == customer, CostBaseline.box_type == box_type).first())
    if not bl:
        bl = (db.query(CostBaseline)
              .filter(CostBaseline.customer == "", CostBaseline.box_type == box_type).first())
        baseline_kind = "无客户同箱型基准"
    baseline_factors = (bl.factors if bl else _gen_factors(box_type))
    if not bl:
        baseline_kind = "箱型默认基准"

    deltas = []
    for ac in actual:
        key = ac["driver"]
        bf = next((f for f in baseline_factors if f.get("driver") == key), None)
        base_val = float(bf["value"]) if bf else float(ac.get("value", 0))
        val = float(ac.get("value", 0))
        diff = round(val - base_val, 2)
        diff_pct = round(diff / base_val * 100, 1) if base_val else 0.0
        deltas.append({
            "dimension": ac.get("dimension", ""), "scene": ac.get("scene", ""),
            "driver": key, "unit": ac.get("unit", ""),
            "value": val, "baseline": base_val,
            "delta": diff, "delta_pct": diff_pct,
        })
    top = sorted(deltas, key=lambda d: abs(d["delta_pct"]), reverse=True)[:3]
    return {
        "work_order_no": plan.work_order_no, "customer": customer, "box_type": box_type,
        "baseline_kind": baseline_kind, "deltas": deltas,
        "top_driver": top[0]["driver"] if top else "",
        "top_delta_pct": top[0]["delta_pct"] if top else 0,
        "above_flag": "超基准" if any(d["delta"] > 0 for d in deltas) else "达标",
    }


async def _llm_summarize_one(it: dict) -> str:
    """对单个工令生成其专属的 LLM 异常动因分析；失败则规则引擎兜底"""
    lines = [f"工令号：{it['work_order_no']}",
             f"客户：{it.get('customer') or '无客户'}，箱型：{it.get('box_type')}，比对基准：{it.get('baseline_kind')}",
             "逐项动因比对（动因 / 业务场景 / 实际值 / 基准值 / 差异 / 差异率）："]
    for d in it["deltas"]:
        lines.append(f"- {d['driver']}（{d['scene']}）: {d['value']} / {d['baseline']} / "
                     f"{d['delta']:+.2f} / {d['delta_pct']:+.1f}%")
    user_msg = "\n".join(lines)
    content = await chat_completion(
        [{"role": "system", "content": CAD_COST_SYSTEM_PROMPT},
         {"role": "user", "content": user_msg}],
        temperature=0.3,
        scene="cost_analysis",
    )
    if content:
        return content
    over = [d for d in it["deltas"] if d["delta"] > 0]
    top = it["top_driver"]
    if not over:
        return (f"（规则引擎兜底）工令 {it['work_order_no']} 各项动因均未超基准，成本可控。")
    return (f"（规则引擎兜底）工令 {it['work_order_no']} 共 {len(over)} 项动因超基准，"
            f"最突出为「{top}」差异率 {it['top_delta_pct']:+.1f}%。"
            f"建议优先核查该工令的用料/工时/能耗投入。")


@router.post("/analyze")
async def analyze_cost(body: AnalyzeIn, db: Session = Depends(get_db)):
    """成本动因分析：支持 单个工令/单个客户全部工令/按箱型全部工令/全部工令，
    每个工令按 同客户+同箱型 → 无客户同箱型 → 箱型默认 基准比对，
    分析结果按最小工令维度保存（cost_analysis，重复分析覆盖）。
    """
    mode = body.mode or "all"
    plans = db.query(SchedulePlan).filter(SchedulePlan.plan_month == "2026-08").all()
    if mode == "work_order":
        if not body.work_order_no:
            raise HTTPException(400, "请选择工令号")
        plans = [p for p in plans if p.work_order_no == body.work_order_no]
        scope_desc = f"单个工令 {body.work_order_no}"
    elif mode == "customer":
        if not body.customer:
            raise HTTPException(400, "请选择客户")
        plans = [p for p in plans if p.customer == body.customer]
        scope_desc = f"客户「{body.customer}」全部工令"
    elif mode == "box_type":
        if not body.box_type:
            raise HTTPException(400, "请选择箱型")
        plans = [p for p in plans if p.box_type == body.box_type]
        scope_desc = f"箱型「{body.box_type}」全部工令"
    else:
        scope_desc = "全部工令"

    if not plans:
        raise HTTPException(404, "该范围内没有可分析的工令")

    # 强制重新分析：清理范围内已分析记录
    if body.force:
        scope_work_orders = {p.work_order_no for p in plans}
        deleted = db.query(CostAnalysis).filter(
            CostAnalysis.work_order_no.in_(scope_work_orders)).delete(synchronize_session=False)
        db.commit()
        # 所有工令均为待分析
        pending = list(plans)
        force_note = f"（强制重新分析，已清理 {deleted} 条历史记录）"
    else:
        # 历史分析过的工令不再分析（跳过）
        analyzed = {r[0] for r in db.query(CostAnalysis.work_order_no).all()}
        pending = [p for p in plans if p.work_order_no not in analyzed]
        force_note = ""
        if not pending:
            return {"scope": mode, "scope_desc": scope_desc, "items": [],
                    "llm_analysis": f"「{scope_desc}」范围内工令均已分析过，无需重复分析。",
                    "saved_count": 0, "skipped_count": len(plans)}

    items = [_analyze_one(p, db) for p in pending]
    # 每个工令生成其专属的 LLM 异常动因分析
    for it in items:
        it["llm_analysis"] = await _llm_summarize_one(it)

    # 按最小工令维度保存（一个工令一条，重复分析覆盖更新）
    saved = 0
    for it in items:
        rec = db.query(CostAnalysis).filter(
            CostAnalysis.work_order_no == it["work_order_no"]).first()
        if rec:
            rec.customer = it["customer"]
            rec.box_type = it["box_type"]
            rec.baseline_kind = it["baseline_kind"]
            rec.deltas = it["deltas"]
            rec.llm_analysis = it["llm_analysis"]
            rec.scope = mode
        else:
            db.add(CostAnalysis(work_order_no=it["work_order_no"], customer=it["customer"],
                                box_type=it["box_type"], baseline_kind=it["baseline_kind"],
                                deltas=it["deltas"], llm_analysis=it["llm_analysis"], scope=mode))
        saved += 1
    db.commit()

    return {"scope": mode, "scope_desc": scope_desc, "items": items,
            "llm_analysis": items[0]["llm_analysis"] if items else "",
            "saved_count": saved,
            "skipped_count": len(plans) - len(pending),
            "force_note": force_note}


@router.get("/analysis-records")
def analysis_records(work_order_no: str | None = None, customer: str | None = None,
                     box_type: str | None = None, db: Session = Depends(get_db)):
    """成本动因分析明细：历史分析过的工令列表（按最小工令维度已保存）"""
    q = db.query(CostAnalysis)
    if work_order_no:
        q = q.filter(CostAnalysis.work_order_no == work_order_no)
    if customer is not None:
        q = q.filter(CostAnalysis.customer == customer)
    if box_type:
        q = q.filter(CostAnalysis.box_type == box_type)
    rows = q.order_by(CostAnalysis.analyzed_at.desc()).all()
    out = []
    for r in rows:
        deltas = r.deltas or []
        top = sorted(deltas, key=lambda d: abs(d.get("delta_pct", 0)), reverse=True)[:3]
        out.append({
            "work_order_no": r.work_order_no, "customer": r.customer, "box_type": r.box_type,
            "baseline_kind": r.baseline_kind, "deltas": deltas, "llm_analysis": r.llm_analysis,
            "scope": r.scope, "analyzed_at": r.analyzed_at.isoformat() if r.analyzed_at else "",
            "top_driver": top[0]["driver"] if top else "",
            "top_delta_pct": top[0]["delta_pct"] if top else 0,
            "above_flag": "超基准" if any(d.get("delta", 0) > 0 for d in deltas) else "达标",
        })
    return out


@router.get("/analysis-summary")
async def analysis_summary(db: Session = Depends(get_db)):
    """异常动因分析汇总：基于历史分析结果中所有超基准工令，按动因维度汇总统计并生成 LLM 总结"""
    rows = db.query(CostAnalysis).order_by(CostAnalysis.analyzed_at.desc()).all()

    # 提取所有超基准工令及其超基准动因
    abnormal_orders: list[dict] = []
    driver_stats: dict[str, dict] = {}  # driver -> {dimension, scene, unit, count, sum_delta_pct, abs_sum_delta_pct}
    dim_driver_count: dict[str, int] = {}

    for r in rows:
        deltas = r.deltas or []
        over = [d for d in deltas if d.get("delta", 0) > 0]
        if not over:
            continue
        abnormal_orders.append({
            "work_order_no": r.work_order_no, "customer": r.customer, "box_type": r.box_type,
            "over_drivers": [d["driver"] for d in over],
        })
        for d in over:
            key = d["driver"]
            if key not in driver_stats:
                driver_stats[key] = {
                    "dimension": d.get("dimension", ""), "scene": d.get("scene", ""),
                    "driver": key, "unit": d.get("unit", ""),
                    "count": 0, "sum_delta_pct": 0.0, "abs_sum_delta_pct": 0.0,
                    "orders": [],
                }
            driver_stats[key]["count"] += 1
            driver_stats[key]["sum_delta_pct"] += d.get("delta_pct", 0)
            driver_stats[key]["abs_sum_delta_pct"] += abs(d.get("delta_pct", 0))
            if r.work_order_no not in driver_stats[key]["orders"]:
                driver_stats[key]["orders"].append(r.work_order_no)

        for d in over:
            dim = d.get("dimension", "")
            dim_driver_count[dim] = dim_driver_count.get(dim, 0) + 1

    # 按异常频次降序排列动因
    sorted_drivers = sorted(driver_stats.values(),
                            key=lambda x: (x["count"], x["abs_sum_delta_pct"]), reverse=True)
    top_dimension = max(dim_driver_count, key=dim_driver_count.get) if dim_driver_count else ""

    # LLM 汇总
    scope_desc = f"共 {len(abnormal_orders)} 个异常工令，涉及 {len(sorted_drivers)} 项动因因子"
    lines = ["异常动因汇总信息：", f"异常工令数：{len(abnormal_orders)}", f"超基准最集中的维度：{top_dimension}",
             "按动因维度汇总（动因 / 出现频次 / 平均差异率 / 涉及工令）："]
    for sd in sorted_drivers[:10]:
        avg_pct = round(sd["sum_delta_pct"] / sd["count"], 1) if sd["count"] else 0
        lines.append(f"- {sd['driver']}（{sd['dimension']}）: 出现 {sd['count']} 次, 平均差异率 {avg_pct:+.1f}%, 涉及 {len(sd['orders'])} 个工令")
    user_msg = "\n".join(lines)

    llm_summary = await chat_completion(
        [{"role": "system", "content": CAD_COST_SUMMARY_PROMPT},
         {"role": "user", "content": user_msg}],
        temperature=0.3,
        scene="cost_summary",
    )
    if not llm_summary:
        worst_driver = sorted_drivers[0] if sorted_drivers else None
        llm_summary = (f"（规则引擎兜底）{scope_desc}。"
                       f"超基准最集中的维度为「{top_dimension}」，"
                       + (f"最突出的异常动因为「{worst_driver['driver']}」（{worst_driver['count']} 次出现）。"
                          if worst_driver else "无异常数据。"))

    return {
        "total_abnormal": len(abnormal_orders),
        "total_analyzed": len(rows),
        "top_dimension": top_dimension,
        "driver_summary": sorted_drivers[:20],
        "llm_summary": llm_summary,
    }