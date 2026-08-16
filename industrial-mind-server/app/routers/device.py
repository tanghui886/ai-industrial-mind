"""设备异常大屏 + 设备管理明细接口（本次使用 mock 示例数据，产线来源于 production_line 配置表）"""
from __future__ import annotations

import random
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ProductionLine

router = APIRouter(prefix="/device", tags=["device"])

# (前缀, 设备类型名)
DEVICE_TYPES = [("WLD", "焊接机器人"), ("COAT", "涂装设备"), ("AIR", "气密检测"),
                ("BEND", "折弯机"), ("CUT", "等离子切割"), ("PRESS", "冲压机"),
                ("CRANE", "起重机"), ("COMP", "空压机"), ("FAN", "风机"), ("CONV", "输送线")]
STATUSES = ["正常", "预警", "警告", "故障"]


def _lines(db: Session) -> list[ProductionLine]:
    """产线列表（来源于 production_line 配置表）"""
    return db.query(ProductionLine).order_by(ProductionLine.id).all()


def _gen_devices(db: Session) -> list[dict]:
    """按 production_line 各产线生成固定 mock 设备明细（确定性随机，每次返回一致）"""
    random.seed(2026)
    devices: list[dict] = []
    seq: dict[str, int] = {}
    for line in _lines(db):
        for _ in range(random.randint(5, 7)):
            prefix, dtype = random.choice(DEVICE_TYPES)
            seq[prefix] = seq.get(prefix, 0) + 1
            health = random.randint(55, 99)
            if health >= 90:
                status = "正常"
            elif health >= 80:
                status = "正常" if random.random() < 0.6 else "预警"
            elif health >= 70:
                status = "预警"
            elif health >= 60:
                status = "警告"
            else:
                status = "故障"
            last = date(2026, 8, 16) - timedelta(days=random.randint(3, 60))
            devices.append({
                "device_id": f"{prefix}-{line.line_code.split('-')[0]}{seq[prefix]:02d}",
                "name": f"{dtype}#{seq[prefix]}",
                "line_code": line.line_code,
                "line_name": line.line_name,
                "device_type": dtype,
                "status": status,
                "health": health,
                "rul_hours": random.randint(50, 3000),
                "temperature": round(random.uniform(38, 88), 1),
                "vibration": round(random.uniform(0.5, 8.5), 2),
                "current_load": random.randint(30, 100),
                "last_maintenance": last.isoformat(),
                "next_maintenance": (last + timedelta(days=random.randint(15, 45))).isoformat(),
                "mtbf_hours": random.randint(800, 4000),
            })
    return devices


@router.get("/list")
def device_list(line_code: str | None = None, status: str | None = None,
                keyword: str | None = None, db: Session = Depends(get_db)):
    """设备管理明细列表（支持按产线/状态/关键字过滤，产线来源于 production_line）"""
    devices = _gen_devices(db)
    rows = devices
    if line_code:
        rows = [d for d in rows if d["line_code"] == line_code]
    if status:
        rows = [d for d in rows if d["status"] == status]
    if keyword:
        kw = keyword.strip().lower()
        rows = [d for d in rows
                if kw in d["name"].lower() or kw in d["device_id"].lower()
                or kw in d["device_type"].lower()]
    return rows


@router.get("/screen")
def device_screen(db: Session = Depends(get_db)):
    """设备异常大屏聚合数据"""
    devices = _gen_devices(db)
    total = len(devices)
    online = sum(1 for d in devices if d["status"] == "正常")
    warn = sum(1 for d in devices if d["status"] in ("预警", "警告"))
    fault = sum(1 for d in devices if d["status"] == "故障")
    avg_health = round(sum(d["health"] for d in devices) / total, 1) if total else 0

    # 各产线状态分布（来源于 production_line）
    by_line = []
    for line in _lines(db):
        ds = [d for d in devices if d["line_code"] == line.line_code]
        by_line.append({
            "line_code": line.line_code, "line_name": line.line_name, "total": len(ds),
            "normal": sum(1 for d in ds if d["status"] == "正常"),
            "warn": sum(1 for d in ds if d["status"] in ("预警", "警告")),
            "fault": sum(1 for d in ds if d["status"] == "故障"),
        })

    # 设备健康度分布直方图
    bins, bin_labels = [0, 0, 0, 0, 0], ["<60", "60-70", "70-80", "80-90", ">=90"]
    for d in devices:
        h = d["health"]
        idx = 0 if h < 60 else 1 if h < 70 else 2 if h < 80 else 3 if h < 90 else 4
        bins[idx] += 1

    # 24 小时异常告警趋势（mock）
    random.seed(11)
    now = datetime.now()
    trend = []
    for i in range(23, -1, -1):
        t = now - timedelta(hours=i)
        trend.append({"time": t.strftime("%H:00"), "count": random.randint(0, 8)})

    # 异常类型分布（mock）
    abnormal_types = [
        {"type": "温度超限", "count": random.randint(3, 12)},
        {"type": "振动异常", "count": random.randint(2, 10)},
        {"type": "压力波动", "count": random.randint(1, 8)},
        {"type": "润滑不良", "count": random.randint(1, 6)},
        {"type": "电气故障", "count": random.randint(0, 4)},
    ]

    # 实时异常告警流（mock）
    alerts = []
    for _i in range(8):
        d = random.choice(devices)
        lv = random.choice(["严重", "警告", "提示"])
        alerts.append({
            "time": (now - timedelta(minutes=random.randint(0, 180))).strftime("%H:%M"),
            "device_id": d["device_id"], "device_name": d["name"], "line_code": d["line_code"],
            "level": lv,
            "message": f"{d['name']} {random.choice(['温度超限', '振动异常', '电流波动', '压力偏低'])}，已触发诊断流程",
            "status": random.choice(["处理中", "待确认", "已关闭"]),
        })
    alerts = sorted(alerts, key=lambda a: a["time"], reverse=True)

    return {
        "kpi": {"total": total, "online": online, "warn": warn, "fault": fault, "avg_health": avg_health},
        "by_line": by_line,
        "health_dist": {"labels": bin_labels, "values": bins},
        "trend": trend,
        "abnormal_types": abnormal_types,
        "alerts": alerts,
    }