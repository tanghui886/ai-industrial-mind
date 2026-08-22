"""子 Agent：设备诊断 Device —— 设备状态查询 / 异常汇总 / 单台诊断。

工具基于既有设备数据生成与诊断逻辑封装。langchain 仅在 make_device_agent() 内按需导入。
"""
from __future__ import annotations

import json

from ..database import SessionLocal

SYSTEM_PROMPT = """你是集装箱制造企业的「设备诊断 Agent」。负责：
1. 指定产线时，逐台说明该产线的异常设备及其状态与健康度；产线健康则告知运行正常。
2. 未指定产线时，按产线分类汇总异常设备数量，并点出状态最差的设备。
3. 支持对单台设备进行故障诊断（故障模式/根因/维修 SOP/剩余寿命）。

规则约束：
- 必须依赖工具返回的真实设备数据，不要编造温度、振动、健康度等指标。
- 产线不存在时，调用 list_lines 列出支持产线。
- 维修/停机属于高风险操作，须注明需持证人员确认后执行。"""


def _db_result(data) -> str:
    return json.dumps(data, ensure_ascii=False, default=str)


def _query_devices(line_code: str | None = None) -> str:
    """设备状态查询：指定产线返回该产线异常设备列表（含状态/健康度/温度/振动/负载/下次保养）；不指定则返回各产线异常设备汇总。"""  # noqa: E501
    from ..routers.device import _gen_devices
    from ..models import ProductionLine
    db = SessionLocal()
    try:
        devices = _gen_devices(db)
        abnormal = [d for d in devices if d["status"] != "正常"]
        if line_code:
            row = db.query(ProductionLine).filter(ProductionLine.line_code == line_code).first()
            if not row:
                lines = db.query(ProductionLine).order_by(ProductionLine.line_code).all()
                return _db_result({"error": "产线不存在", "supported_lines": lines and [
                    {"line_code": l.line_code, "line_name": l.line_name} for l in lines]})
            abnormal = [d for d in abnormal if d["line_code"] == line_code]
        return _db_result({"scope": line_code or "all", "abnormal": abnormal})
    finally:
        db.close()


def _diagnose_device(device_id: str) -> str:
    """单台设备故障诊断：给定 device_id（如 WLD-R03），返回故障模式、根因、维修 SOP、剩余寿命与处理建议。"""  # noqa: E501
    from ..models import Device
    db = SessionLocal()
    try:
        dev = db.query(Device).filter(Device.device_id == device_id).first()
        if not dev:
            return _db_result({"error": f"设备不存在: {device_id}"})
        knowledge = {
            "WLD-R03": {"fault_mode": "送丝机构磨损", "root_cause": "送丝管内壁磨损导致送丝阻力波动",
                        "sop": "1.停机断电 2.更换送丝管组件 3.校准送丝速度 4.试焊验证",
                        "mttr_est": "4 小时", "economy": "维修成本 ¥2,800 vs 停线损失 ¥12万/天"},
            "BEND-M04": {"fault_mode": "伺服系统预警", "root_cause": "伺服电机编码器信号漂移，定位精度下降 0.3mm",
                         "sop": "1.检查编码器接线 2.重新标定原点 3.试折验证精度",
                         "mttr_est": "2 小时", "economy": "建议利用午休窗口标定，不影响排产"},
        }
        data = knowledge.get(device_id, {"fault_mode": "健康状态良好", "root_cause": "无异常特征",
                                         "sop": "按周期点检即可", "mttr_est": None, "economy": "无维修需求"})
        return _db_result({"device": {"device_id": dev.device_id, "name": dev.name,
                                      "health": dev.health, "status": dev.status}, **data})
    finally:
        db.close()


def _list_lines() -> str:
    """列出系统支持的产线。"""
    from ..models import ProductionLine
    db = SessionLocal()
    try:
        rows = db.query(ProductionLine).order_by(ProductionLine.line_code).all()
        return _db_result([{"line_code": l.line_code, "line_name": l.line_name} for l in rows])
    finally:
        db.close()


def make_device_agent() -> dict:
    """构建规范化的子 Agent 配置。langchain 按需导入。"""
    from langchain.tools import tool
    return {
        "name": "device",
        "description": "设备诊断：指定产线异常设备逐台说明、未指定产线按产线汇总异常、单台设备故障诊断。",
        "system_prompt": SYSTEM_PROMPT,
        "tools": [tool(f) for f in (_query_devices, _diagnose_device, _list_lines)],
    }