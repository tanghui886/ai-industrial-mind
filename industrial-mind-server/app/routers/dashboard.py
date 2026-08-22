"""产线总览大屏接口"""
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Alert, Device, ProductionLine, ScheduleDaily
from ..services.planning_engine import capacity_summary

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# 产线运行状态（设备实时数据，演示值）
LINE_RUNTIME = {
    "PD-D": {"status": "运行", "current_model": "SC-40HC（40ft 标准箱）", "plan": 42, "actual": 38},
    "BS-A": {"status": "运行", "current_model": "RF-20RS（20ft 冷藏箱）", "plan": 28, "actual": 26},
    "JS-A": {"status": "降速", "current_model": "OT-40OP（40ft 开顶箱）", "plan": 18, "actual": 14},
    "JS-B": {"status": "检修", "current_model": "GP-20DV（20ft 干货箱）", "plan": 22, "actual": 0},
    "FX-A": {"status": "停机", "current_model": "HQ-40HC（40ft 高箱）", "plan": 30, "actual": 0},
}


@router.get("/overview")
def overview(line_code: str = "PD-D", db: Session = Depends(get_db)):
    today = date.today()
    lines = db.query(ProductionLine).all()
    line_status = []
    for l in lines:
        rt = LINE_RUNTIME.get(l.line_code, {"status": "运行", "current_model": "-", "plan": 0, "actual": 0})
        ach = round(rt["actual"] / rt["plan"] * 100, 1) if rt["plan"] else 0
        line_status.append({
            "line_code": l.line_code, "line_name": l.line_name, "factory": l.factory_code,
            "status": rt["status"], "current_model": rt["current_model"],
            "plan": rt["plan"], "actual": rt["actual"], "achievement": f"{ach}%",
        })

    kpi = {
        "today_plan_teu": 42, "today_actual_teu": 38,
        "achievement_rate": "90.5%", "oee": "84.2%",
        "device_online_rate": "96.8%", "device_online_text": "在线 30/31 台",
        "open_alerts": db.query(Alert).filter(Alert.status != "已关闭").count(),
        "severe_alerts": db.query(Alert).filter(Alert.status != "已关闭", Alert.level == "严重").count(),
    }

    # 近7日产能达成（计划/实际，TEU）
    import random
    random.seed(7)
    labels, plan_series, actual_series = [], [], []
    d = today
    days = []
    for i in range(7):
        days.append(d)
        d = d.fromordinal(d.toordinal() - 1)
    days = list(reversed(days))
    for i, dd in enumerate(days):
        labels.append(dd.strftime("%m-%d") if i < 6 else "今日")
        booked = (db.query(ScheduleDaily)
                  .filter(ScheduleDaily.line_code == line_code, ScheduleDaily.schedule_date == dd).all())
        planned = sum(r.teu or 0 for r in booked)
        plan_series.append(max(planned, 40))
        actual_series.append(int(max(planned, 40) * (0.9 if dd <= today else 1.0)))

    devices = [{
        "device_id": dv.device_id, "name": dv.name, "health": dv.health,
        "status": dv.status, "rul_hours": dv.rul_hours, "rul_note": dv.rul_note,
    } for dv in db.query(Device).filter(Device.line_code == line_code).all()]

    alerts = [{
        "time": a.alert_time, "source_agent": a.source_agent, "level": a.level,
        "message": a.message, "status": a.status,
    } for a in db.query(Alert).order_by(Alert.id.desc()).all()]

    month = capacity_summary(db, line_code, today.year, today.month)

    return {"kpi": kpi, "line_status": line_status,
            "capacity_chart": {"labels": labels, "plan": plan_series, "actual": actual_series},
            "devices": devices, "alerts": alerts, "month_summary": month}
