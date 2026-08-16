"""Agent 能力接口（设备诊断/物料缺口/堆存风险/成本动因）"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Alert, Device, Material, ProductionLine, SchedulePlan
from ..services.material_usage import material_usage_by_status

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("/diagnosis")
def diagnosis(device_id: str = "WLD-R03", db: Session = Depends(get_db)):
    """设备故障诊断 Agent（演示：基于设备健康数据生成诊断结论）"""
    dev = db.query(Device).filter(Device.device_id == device_id).first()
    if not dev:
        return {"message": "设备不存在"}
    knowledge = {
        "WLD-R03": {
            "fault_mode": "送丝机构磨损", "root_cause": "送丝管内壁磨损导致送丝阻力波动（FFT频谱 120Hz 异常分量）",
            "sop": "1.停机断电 2.更换送丝管组件 3.校准送丝速度 4.试焊验证",
            "rul": f"{dev.rul_hours} 小时", "mttr_est": "4 小时",
            "economy": "维修成本 ¥2,800 vs 停线损失 ¥12万/天 → 建议立即安排检修窗口",
        },
        "BEND-M04": {
            "fault_mode": "伺服系统预警", "root_cause": "伺服电机编码器信号漂移，定位精度下降 0.3mm",
            "sop": "1.检查编码器接线 2.重新标定原点 3.试折验证精度",
            "rul": f"{dev.rul_hours} 小时", "mttr_est": "2 小时",
            "economy": "建议利用午休窗口标定，不影响排产",
        },
    }
    data = knowledge.get(device_id, {
        "fault_mode": "健康状态良好", "root_cause": "无异常特征",
        "sop": "按周期点检即可", "rul": f"{dev.rul_hours} 小时", "mttr_est": "-",
        "economy": "无维修需求"})
    return {"device": {"device_id": dev.device_id, "name": dev.name, "health": dev.health,
                       "status": dev.status}, **data,
            "safety_note": "⚠️ 诊断结果由 AI 生成，维修作业须由持证人员现场确认后执行。"}


@router.get("/quality")
def quality(db: Session = Depends(get_db)):
    """质量异常分析 Agent（演示）"""
    return {
        "spc": {"dimension": "箱体长度", "cl": "12192mm", "ucl": "+3mm", "lcl": "-3mm",
                "cpk": 1.42, "trend": "stable"},
        "defects": [
            {"type": "焊缝气孔", "count": 3, "root_cause": "送丝机构磨损（关联设备 DFQD 焊接#3）",
             "cost": "材料浪费 ¥4,200", "action": "触发设备诊断 Agent 联查"},
            {"type": "漆面流挂", "count": 1, "root_cause": "喷涂粘度偏高（批次 P-2026-0812）",
             "cost": "返工工时 6h", "action": "调整粘度参数并锁定批次"},
        ],
        "airtight": {"pass_rate": "99.2%", "last_fail": "2026-08-11 漏点定位：门端密封条（已返修）"},
    }


@router.get("/dispatch")
def dispatch(db: Session = Depends(get_db)):
    """工单调度 Agent（演示）"""
    return {
        "work_orders": [
            {"wo": "WO-2026-0814-01", "type": "焊接机器人#3 送丝机构更换", "skills": "机器人+电气",
             "priority": 95, "window": "今日 13:00~17:00（换班间隙）", "status": "待班组长接单",
             "spare_parts": "送丝管组件 ×1（库存充足）"},
            {"wo": "WO-2026-0814-02", "type": "折弯机伺服标定", "skills": "电气",
             "priority": 70, "window": "明日午休 12:00~13:00", "status": "已派单",
             "spare_parts": "无需备件"},
        ],
        "rule": "总装线停线 > 焊接线停线 > 涂装线降速；维修窗口避开排产高峰",
    }


@router.get("/material-gap")
def material_gap(factory: str | None = None, db: Session = Depends(get_db)):
    """物料缺口 Agent：按工厂列出存在缺口的物料（在库 - 订单扣减 - 草稿 < 0 即缺口）"""
    mats = db.query(Material).order_by(Material.factory, Material.id).all()
    rows = []
    for m in mats:
        if factory and m.factory != factory:
            continue
        order_deducted = material_usage_by_status(db, m, ["pending_approval"])
        draft_usage = material_usage_by_status(db, m, ["draft"])
        remainder = m.in_stock_units - order_deducted - draft_usage
        gap = 0 if remainder > 0 else abs(remainder)
        rows.append({
            "material": m.name, "code": m.code, "unit": m.unit, "factory": m.factory,
            "in_stock": m.in_stock_units, "order_deducted": round(order_deducted),
            "gap": round(gap), "status": "需补货" if gap > 0 else "充足",
            "action": "建议锁定在途订单并评估受影响工令排产调整" if gap > 0 else "库存充足，无需补货",
        })
    return {"factory": factory or "全部", "gaps": rows,
            "summary": f"共 {sum(1 for r in rows if r['gap'] > 0)} 项物料需补货"}


@router.get("/storage-risk")
def storage_risk(db: Session = Depends(get_db)):
    """堆存风险 Agent：按产线统计堆存，列出剩余空间为负（爆仓风险）的产线"""
    lines = db.query(ProductionLine).order_by(ProductionLine.factory_code, ProductionLine.id).all()
    storage_units: dict[str, int] = {}
    pre_storage: dict[str, int] = {}
    for code, qty, status in (db.query(SchedulePlan.line_code, SchedulePlan.quantity,
                                       SchedulePlan.status).all()):
        if status == "confirmed":
            storage_units[code] = storage_units.get(code, 0) + qty
        elif status in ("pending_approval", "draft"):
            pre_storage[code] = pre_storage.get(code, 0) + qty
    rows = []
    for l in lines:
        remaining = l.storage_capacity - storage_units.get(l.line_code, 0) - pre_storage.get(l.line_code, 0)
        rows.append({"line_code": l.line_code, "line_name": l.line_name, "factory_code": l.factory_code,
                     "capacity": l.storage_capacity, "storage_units": storage_units.get(l.line_code, 0),
                     "pre_storage": pre_storage.get(l.line_code, 0), "remaining": remaining,
                     "status": "风险" if remaining < 0 else "正常"})
    risks = [r for r in rows if r["status"] == "风险"]
    return {"lines": rows, "risk_count": len(risks),
            "summary": f"共 {len(risks)} 条产线存在爆仓风险" if risks else "各产线堆存均在安全范围内"}


@router.get("/cost-analysis")
def cost_analysis(month: str = "2026-08", db: Session = Depends(get_db)):
    """成本动因分析 Agent（演示：单箱成本拆解）"""
    plans = db.query(SchedulePlan).filter(SchedulePlan.plan_month == month).all()
    total_teu = sum(p.teu for p in plans) or 1
    return {
        "month": month,
        "per_box_cost": [
            {"item": "直接材料", "amount": 14200, "ratio": "62%", "driver": "箱型设计/领料管控（移动加权平均）"},
            {"item": "人工成本", "amount": 3400, "ratio": "15%", "driver": "报工工时（计划发薪+年终奖）"},
            {"item": "制造费用", "amount": 3900, "ratio": "17%", "driver": "电费/燃气按报工工时，折旧按耗电量"},
            {"item": "交付成本", "amount": 1400, "ratio": "6%", "driver": "箱量×费率（堆存/运输/海运）"},
        ],
        "total_teu": total_teu,
        "anomaly": ["40HCDD 单箱材料成本环比 +4.2%（角件补货溢价）"],
        "rules": "分摊颗粒度：工令+工段+物料编码；跨月费用自动结转",
    }
