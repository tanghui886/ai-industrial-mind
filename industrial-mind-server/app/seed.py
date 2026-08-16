"""种子数据：对齐设计稿与方案 v6 示例（演示数据，首次启动自动生成）"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from .models import (Alert, Approval, BoxType, Device, Factory,
                     IntentionOrder, Material, MonthlyPlanTarget,
                     Notification, ProductionLine, RolePermission,
                     ScheduleDaily, SchedulePlan, User)
from .permissions import DEFAULT_PERMS

FACTORIES = [
    ("DFQD", "启东工厂"), ("DFSH", "上海工厂"), ("DFNT", "南通工厂"), ("DFLYG", "连云港工厂"),
]
LINES = [
    ("QD-D", "启东D线（特箱线）", "DFQD", "特种箱", 180, 600, 320),
    ("SH-A", "上海A线", "DFSH", "标准箱", 260, 800, 450),
    ("NT-A", "南通A线", "DFNT", "标准箱", 260, 800, 380),
    ("NT-B", "南通B线", "DFNT", "标准箱", 240, 750, 410),
    ("LYG-A", "连云港A线", "DFLYG", "标准箱", 240, 700, 360),
]
# code, name, category, min, max, std, teu, cteu
BOX_TYPES = [
    ("20GP", "20'标准干货箱", "标准干货箱", 90, 150, 120, 1.0, 1.0),
    ("20OS", "20'开顶箱", "标准干货箱", 90, 150, 120, 1.0, 1.1),
    ("40GP", "40'标准干货箱", "标准大箱", 80, 100, 90, 2.0, 2.0),
    ("40HC", "40'HC标准干货箱", "标准大箱", 80, 100, 90, 2.0, 2.0),
    ("40HCDD", "40'HC双开门箱", "大型特种箱", 15, 35, 25, 2.0, 2.4),
    ("40HCFOS", "40'HC框架箱", "大型特种箱", 15, 35, 25, 2.0, 2.4),
    ("20DUOCON", "20'DUOCON特种小箱", "特种小箱", 80, 100, 90, 1.0, 1.2),
    ("20HCFOS", "20'HC框架箱", "特种小箱", 80, 100, 90, 1.0, 1.2),
    ("20储能箱", "20'储能箱", "储能箱系列", 35, 50, 42, 1.0, 1.3),
    ("20HC储能箱", "20'HC储能箱", "储能箱系列", 35, 50, 42, 2.0, 2.6),
    ("Ener C+", "Ener C+ 新能源箱", "Ener系列", 26, 50, 38, 2.0, 2.6),
    ("Ener D", "Ener D 新能源箱", "Ener系列", 26, 50, 38, 2.0, 2.6),
    ("Ener D Max", "Ener D Max加长版", "Ener系列", 15, 35, 25, 2.0, 2.6),
    ("Ener E", "Ener E 新能源箱", "Ener系列", 26, 50, 38, 2.0, 2.6),
    ("Ener S", "Ener S 新能源箱", "Ener系列", 26, 50, 38, 2.0, 2.6),
    ("Ener X", "Ener X 新能源箱", "Ener系列", 26, 50, 38, 2.0, 2.6),
    ("Ener H", "Ener H 新能源箱", "Ener系列", 26, 50, 38, 2.0, 2.6),
    ("Ener W", "Ener W 新能源箱", "Ener系列", 26, 50, 38, 2.0, 2.6),
    ("液冷方舱", "40'液冷方舱", "大型特种箱", 15, 35, 25, 2.0, 2.4),
    ("房屋箱", "40'房屋箱", "房屋箱/光伏", 24, 35, 30, 2.0, 2.4),
    ("光伏平板", "40'光伏平板箱", "房屋箱/光伏", 24, 35, 30, 2.0, 2.4),
    ("20气瓶箱", "20'气瓶箱", "气瓶箱", 20, 20, 20, 1.0, 1.3),
    ("40气瓶箱", "40'气瓶箱", "气瓶箱", 20, 20, 20, 2.0, 2.6),
    ("45HC气瓶箱", "45'HC气瓶箱", "气瓶箱", 20, 20, 20, 2.25, 2.9),
    ("30ft滚装车架", "30ft滚装车架", "滚装车架", 29, 35, 32, 1.5, 1.8),
    ("40ft滚装车架", "40ft 130ton滚装车架", "滚装车架", 29, 35, 32, 2.0, 2.4),
    ("岸电箱", "20'岸电箱", "储能箱系列", 35, 50, 42, 1.0, 1.3),
]

# QD-D 2026-08 工令（对齐设计稿排产工作台示例 + 铺量数据）
# (工令号, 客户, 箱型, 数量, 开始, 结束, 状态, 类型, 交付地, 备注)
AUG_ORDERS = [
    ("DFQD-2026-268-DS", "航天科工", "液冷方舱", 28, "2026-08-26", "2026-08-31", "confirmed", "批量", "武汉", ""),
    ("DFQD-2026-269-DS", "江苏气瓶", "40气瓶箱", 40, "2026-08-24", "2026-08-28", "confirmed", "批量", "南京", ""),
    ("DFQD-2026-270-DS", "中远海运", "20GP", 10, "2026-08-24", "2026-08-24", "confirmed", "样箱", "上海", "客户验样"),
    ("DFQD-2026-271-DS", "东方国际", "20GP", 240, "2026-08-03", "2026-08-07", "completed", "批量", "上海", ""),
    ("DFQD-2026-272-DS", "中远海运", "40HC", 180, "2026-08-03", "2026-08-10", "completed", "批量", "上海", ""),
    ("DFQD-2026-273-DS", "Seaco", "20OS", 120, "2026-08-03", "2026-08-07", "completed", "批量", "宁波", ""),
    ("DFQD-2026-274-DS", "Triton", "40GP", 120, "2026-08-10", "2026-08-14", "confirmed", "批量", "青岛", ""),
    ("DFQD-2026-275-DS", "Enercore", "Ener D", 50, "2026-08-13", "2026-08-14", "confirmed", "小批量", "上海", ""),
    ("DFQD-2026-276-DS", "中建集成", "房屋箱", 24, "2026-08-13", "2026-08-17", "confirmed", "批量", "启东", ""),
    ("DFQD-2026-277-DS", "宁德时代", "20储能箱", 84, "2026-08-13", "2026-08-17", "confirmed", "批量", "宁德", "含Pack预装"),
    ("DFQD-2026-S01-DS", "东方国际", "20GP", 20, "2026-08-06", "2026-08-06", "confirmed", "样箱", "上海", "现场插单样箱"),
    ("DFQD-2026-278-DS", "阳光电源", "光伏平板", 60, "2026-08-18", "2026-08-25", "confirmed", "批量", "合肥", ""),
    ("DFQD-2026-279-DS", "东方外贸", "40HC", 90, "2026-08-19", "2026-08-21", "confirmed", "小批量", "上海", ""),
    ("DFQD-2026-280-DS", "华东储能", "20储能箱", 56, "2026-08-20", "2026-08-21", "confirmed", "批量", "上海", ""),
    ("DFQD-2026-281-DS", "中远海运", "40HC", 120, "2026-08-03", "2026-08-12", "confirmed", "批量", "上海", ""),
    ("DFQD-2026-282-DS", "马士基", "Ener C+", 80, "2026-08-10", "2026-08-17", "draft", "批量", "上海", "AI建议提前2天避开物料缺口"),
    ("DFQD-2026-283-DS", "MSC", "20GP", 200, "2026-08-17", "2026-08-24", "pending_approval", "批量", "宁波", ""),
    ("DFQD-2026-284-DS", "达飞轮船", "40HC", 150, "2026-08-20", "2026-08-28", "draft", "批量", "上海", ""),
]
SEP_ORDERS = [
    ("DFQD-2026-285-DS", "中远海运", "40HCDD", 75, "2026-09-03", "2026-09-09", "confirmed", "批量", "上海", ""),
    ("DFQD-2026-286-DS", "MSC", "40HC", 90, "2026-09-01", "2026-09-04", "confirmed", "批量", "宁波", ""),
    ("DFQD-2026-287-DS", "Seaco", "20GP", 200, "2026-09-07", "2026-09-11", "confirmed", "批量", "宁波", ""),
    ("DFQD-2026-288-DS", "马士基", "Ener C+", 40, "2026-09-10", "2026-09-11", "confirmed", "小批量", "上海", ""),
    ("DFQD-2026-289-DS", "东方国际", "40HC", 120, "2026-09-14", "2026-09-18", "confirmed", "批量", "上海", ""),
    ("DFQD-2026-290-DS", "宁德时代", "20储能箱", 100, "2026-09-21", "2026-09-24", "confirmed", "批量", "宁德", ""),
    ("DFQD-2026-291-DS", "Triton", "40GP", 80, "2026-09-22", "2026-09-24", "confirmed", "批量", "青岛", ""),
    ("DFQD-2026-292-DS", "中建集成", "房屋箱", 30, "2026-09-28", "2026-09-30", "draft", "批量", "启东", ""),
    ("DFQD-2026-293-DS", "阳光电源", "光伏平板", 40, "2026-09-14", "2026-09-17", "pending_approval", "批量", "合肥", ""),
]
OCT_ORDERS = [
    ("DFQD-2026-301-DS", "中远海运", "20GP", 300, "2026-10-08", "2026-10-14", "confirmed", "批量", "上海", ""),
    ("DFQD-2026-302-DS", "达飞轮船", "40HC", 100, "2026-10-15", "2026-10-21", "confirmed", "批量", "上海", ""),
    ("DFQD-2026-303-DS", "Enercore", "Ener E", 50, "2026-10-22", "2026-10-27", "draft", "批量", "上海", ""),
]
OTHER_LINE_ORDERS = [
    ("SH-A", "DFSH-2026-118-DS", "中远海运", "40HC", 260, "2026-08-05", "2026-08-11", "confirmed"),
    ("SH-A", "DFSH-2026-119-DS", "长荣海运", "20GP", 300, "2026-08-12", "2026-08-15", "confirmed"),
    ("NT-A", "DFNT-2026-207-DS", "赫伯罗特", "40HC", 240, "2026-08-06", "2026-08-12", "confirmed"),
    ("NT-B", "DFNT-2026-156-DS", "阳明海运", "20GP", 280, "2026-08-10", "2026-08-13", "confirmed"),
    ("LYG-A", "DFLYG-2026-089-DS", "现代商船", "40GP", 200, "2026-08-11", "2026-08-16", "confirmed"),
]

DEVICES = [
    ("WLD-R03", "焊接机器人#3", "QD-D", 92, "正常", 1200, ""),
    ("COAT-L01", "涂装线", "QD-D", 78, "预警", 560, "建议下周点检"),
    ("AIR-T02", "气密检测设备", "QD-D", 88, "正常", 890, ""),
    ("BEND-M04", "折弯机", "QD-D", 65, "警告", 320, "伺服系统需关注"),
    ("CUT-P01", "等离子切割机", "QD-D", 95, "正常", 1500, ""),
]
ALERTS = [
    ("08:42", "设备Agent", "严重", "焊接机器人#3轴2温度异常，已触发诊断流程", "处理中"),
    ("08:15", "工艺Agent", "警告", "涂装线排风压差偏低，可能影响漆面固化", "待确认"),
    ("07:50", "排产Agent", "提示", "QD-D 8月14日班次计划已下发至MES", "已关闭"),
    ("07:20", "设备Agent", "严重", "折弯机伺服报警，维修工单已生成（WO-2026-0814-02）", "处理中"),
    ("06:55", "质量Agent", "警告", "气密检测工位节拍超时，建议排查密封垫老化", "待确认"),
]
# (code, name, category, factory, stock_note, in_stock_units, order_deducted_units,
#  support_units, in_transit_units, purchase_units, arrival_date, status)
MATERIALS = [
    # 青岛 DFQD
    ("STEEL", "耐候钢SPA-H", "钢板", "DFQD", "当前库存2600吨", 2600, 1800, 800, 600, 1200, date(2026, 9, 5), "充足"),
    ("PAINT", "环氧防腐涂料", "油漆", "DFQD", "底漆+面漆库存", 6500, 4500, 2000, 0, 1500, None, "充足"),
    ("CORNER", "角件/锁具", "角件", "DFQD", "库存约600箱当量", 1500, 900, 600, 400, 800, date(2026, 8, 30), "需补货"),
    ("FLOOR", "木地板", "地板", "DFQD", "进口硬木库存", 5200, 3700, 1500, 0, 600, None, "充足"),
    ("LOCK", "锁杆/铰链", "五金", "DFQD", "常规安全库存", 4200, 3000, 1200, 0, 400, None, "充足"),
    # 上海 DFSH
    ("STEEL-SH", "耐候钢SPA-H", "钢板", "DFSH", "在库1900吨", 1900, 1400, 620, 450, 900, date(2026, 9, 8), "充足"),
    ("PAINT-SH", "环氧防腐涂料", "油漆", "DFSH", "底漆+面漆库存", 4800, 3300, 1600, 0, 1200, None, "充足"),
    ("CORNER-SH", "角件/锁具", "角件", "DFSH", "库存约450箱当量", 1100, 700, 480, 300, 600, date(2026, 9, 1), "需补货"),
    ("FLOOR-SH", "木地板", "地板", "DFSH", "进口硬木库存", 3900, 2800, 1100, 0, 500, None, "充足"),
    ("LOCK-SH", "锁杆/铰链", "五金", "DFSH", "常规安全库存", 3100, 2200, 900, 0, 300, None, "充足"),
    # 南通 DFNT
    ("STEEL-NT", "耐候钢SPA-H", "钢板", "DFNT", "在库2100吨", 2100, 1600, 700, 500, 1000, date(2026, 9, 6), "充足"),
    ("PAINT-NT", "环氧防腐涂料", "油漆", "DFNT", "底漆+面漆库存", 5400, 3800, 1800, 0, 1100, None, "充足"),
    ("CORNER-NT", "角件/锁具", "角件", "DFNT", "库存约520箱当量", 1300, 850, 560, 350, 700, date(2026, 8, 31), "需补货"),
    ("FLOOR-NT", "木地板", "地板", "DFNT", "进口硬木库存", 4600, 3400, 1300, 0, 550, None, "充足"),
    ("LOCK-NT", "锁杆/铰链", "五金", "DFNT", "常规安全库存", 3600, 2600, 950, 0, 350, None, "充足"),
    # 连云港 DFLYG
    ("STEEL-LYG", "耐候钢SPA-H", "钢板", "DFLYG", "在库1700吨", 1700, 1200, 560, 400, 800, date(2026, 9, 9), "充足"),
    ("PAINT-LYG", "环氧防腐涂料", "油漆", "DFLYG", "底漆+面漆库存", 4300, 3000, 1400, 0, 1000, None, "充足"),
    ("CORNER-LYG", "角件/锁具", "角件", "DFLYG", "库存约400箱当量", 1000, 650, 430, 280, 550, date(2026, 9, 2), "需补货"),
    ("FLOOR-LYG", "木地板", "地板", "DFLYG", "进口硬木库存", 3500, 2500, 1000, 0, 450, None, "充足"),
    ("LOCK-LYG", "锁杆/铰链", "五金", "DFLYG", "常规安全库存", 2800, 2000, 800, 0, 300, None, "充足"),
]


def _seed_materials(db: Session) -> None:
    """幂等写入物料（含各工厂 mock 数据）：按 code 存在则更新，否则插入"""
    units = {"STEEL": "吨", "PAINT": "吨", "CORNER": "箱", "FLOOR": "张", "LOCK": "套"}
    gaps = {"CORNER": 320}  # 需补货物料缺口
    for m in MATERIALS:
        (code, name, category, factory, stock_note, in_stock, deduct,
         support, in_transit, purchase, arrival, status) = m
        row = db.query(Material).filter(Material.code == code).first()
        base = code.split("-")[0]
        fields = dict(name=name, category=category, factory=factory,
                      unit=units.get(base, ""), stock_note=stock_note,
                      in_stock_units=in_stock, order_deducted_units=deduct,
                      gap_units=gaps.get(base, 0), support_units=support,
                      in_transit_units=in_transit, purchase_units=purchase,
                      arrival_date=arrival, status=status)
        if row:
            for k, v in fields.items():
                setattr(row, k, v)
        else:
            db.add(Material(code=code, **fields))


def _spread(quantity: int, n: int) -> list[int]:
    """把 quantity 尽量均匀分配到 n 天"""
    base, rem = divmod(quantity, n)
    return [base + (1 if i < rem else 0) for i in range(n)]


def _mk_plan(db: Session, seq: int, line: str, wo: str, customer: str, box_code: str,
             qty: int, start: str, end: str, status: str, order_type: str = "批量",
             location: str = "上海", remark: str = "", source: str = "manual",
             creator: str = "李计划") -> None:
    box = db.query(BoxType).filter(BoxType.code == box_code).first()
    teu = int(qty * float(box.teu_factor))
    cteu = int(qty * float(box.cteu_factor))
    s, e = date.fromisoformat(start), date.fromisoformat(end)
    # 仅排工作日
    days = [s + timedelta(days=i) for i in range((e - s).days + 1)]
    days = [d for d in days if d.weekday() < 5]
    if not days:
        days = [s]
    month_key = f"{s.year:04d}-{s.month:02d}"
    plan = SchedulePlan(
        plan_id=f"PLAN-{line}-{seq:04d}", plan_month=month_key,
        factory_code={"QD-D": "DFQD", "SH-A": "DFSH", "NT-A": "DFNT", "NT-B": "DFNT", "LYG-A": "DFLYG"}[line],
        line_code=line, work_order_no=wo, customer=customer, box_type=box_code,
        quantity=qty, teu=teu, cteu=cteu, production_deadline="按时",
        delivery_status="按时", order_source="自接单", trade_type="外贸",
        delivery_location=location, remark=remark, daily_capacity=box.daily_capacity_std,
        daily_planned_qty=qty // len(days), start_date=s, end_date=e,
        order_type=order_type, status=status, source=source, created_by=creator,
        serial_no="", contract_no=f"CT-{2026}{seq:04d}", order_confirm_no=f"SP-2026-{seq:03d}",
    )
    db.add(plan)
    db.flush()
    alloc = _spread(qty, len(days))
    for d, q in zip(days, alloc):
        db.add(ScheduleDaily(plan_id=plan.plan_id, work_order_no=wo, line_code=line,
                             schedule_date=d, planned_qty=q, teu=int(q * float(box.teu_factor)),
                             is_workday=True))


APPROVALS = [
    dict(approval_no="AP-2026-0814-003", approval_type="排产变更", title="QD-D排产变更：插入样箱订单（Ener C+ 2台）",
         priority="高优先级", applicant="李明", applicant_role="计划员",
         submitted_at=datetime(2026, 8, 14, 10, 23), affect_lines="QD-D 特箱线",
         expect_effect_time="2026-08-14 12:00", risk_level="中风险", related_agent="Scheduler-Agent v2.4",
         need_countersign=True, status="pending",
         detail={
             "reason": "客户东方国际于8月13日提交加急样箱订单（PO-2026-0813-91），要求8月18日前交付首件。当前QD-D白班计划已满，AI建议插入样箱订单并后移部分低优先级常规订单。",
             "plan_compare": {
                 "original": "8/14 白班常规订单 DFQD-2026-278-DS；样箱订单未排入；首件交付 8月21日",
                 "new": "8/14 白班插入样箱订单首件；DFQD-2026-278-DS 部分后移至 8/16~8/17；首件交付 8月17日",
             },
             "impacts": [
                 {"type": "产能影响", "content": "白班利用率从 94% 降至 87%，损失约 14 标准箱当量"},
                 {"type": "物料影响", "content": "样箱所需耐候钢/角件库存充足；常规订单后移不影响采购计划"},
                 {"type": "交期影响", "content": "样箱交期提前 4 天；2 个常规工令整体后移 1.5 天"},
             ],
             "attachments": ["智能排产建议报告.pdf", "物料齐套检查.xlsx"],
             "timeline": [
                 {"node": "李明（计划员）提交审批", "time": "2026-08-14 10:23"},
                 {"node": "Scheduler-Agent 完成 AI 分析（风险评级：中）", "time": "2026-08-14 10:24"},
                 {"node": "待计划主管审批", "time": "当前节点"},
             ],
         }),
    dict(approval_no="AP-2026-0814-002", approval_type="紧急维修", title="焊接机器人M-204送丝机构停机紧急维修",
         priority="紧急", applicant="王强", applicant_role="设备主管",
         submitted_at=datetime(2026, 8, 14, 9, 45), affect_lines="QD-D 焊接工段",
         expect_effect_time="立即", risk_level="高风险", related_agent="Device-Agent v1.8",
         need_countersign=True, status="pending",
         detail={
             "reason": "焊接机器人#3送丝机构磨损（RUL剩余约48小时），FFT频谱异常，建议立即停机更换送丝管组件，避免批量焊接缺陷。",
             "plan_compare": {"original": "继续生产至计划检修日（8/21），期间焊缝质量风险持续累积",
                              "new": "今日 13:00~17:00 停机检修，利用换班间隙完成，避开排产高峰"},
             "impacts": [
                 {"type": "产能影响", "content": "占用4小时检修窗口，当日排产减少约12台当量，可通过周末加班追回"},
                 {"type": "物料影响", "content": "送丝管备件库存2套，满足本次更换"},
                 {"type": "交期影响", "content": "DFQD-2026-283-DS 交期不受影响"},
             ],
             "attachments": ["设备诊断报告.pdf"],
             "timeline": [
                 {"node": "Device-Agent 触发故障告警", "time": "2026-08-14 08:42"},
                 {"node": "王强（设备主管）提交紧急维修审批", "time": "2026-08-14 09:45"},
                 {"node": "待生产主管+设备经理双签", "time": "当前节点"},
             ],
         }),
    dict(approval_no="AP-2026-0813-006", approval_type="采购申请", title="耐候钢SPA-H追加采购申请（200吨当量）",
         priority="高优先级", applicant="陈晨", applicant_role="采购专员",
         submitted_at=datetime(2026, 8, 13, 16, 20), affect_lines="全部产线",
         expect_effect_time="2026-08-20前到货", risk_level="中风险", related_agent="SupplyChain-Agent v1.5",
         need_countersign=False, status="pending",
         detail={
             "reason": "9月排产计划新增储能箱/40HC工令，钢板库存仅满足800台当量，缺口200台当量需在9/5前到货。",
             "plan_compare": {"original": "维持现有库存，9月中旬面临缺料停线风险",
                              "new": "追加采购200吨当量，8/30前到货，锁定9月排产"},
             "impacts": [
                 {"type": "产能影响", "content": "避免9月中旬缺料停线（预计损失3天产能）"},
                 {"type": "物料影响", "content": "供应商宝钢确认8/30可交货"},
                 {"type": "成本影响", "content": "紧急采购溢价约8%，增加成本约¥12万"},
             ],
             "attachments": ["供应商报价单.pdf"],
             "timeline": [
                 {"node": "SupplyChain-Agent 触发缺料预警", "time": "2026-08-13 15:30"},
                 {"node": "陈晨（采购专员）提交采购申请", "time": "2026-08-13 16:20"},
                 {"node": "待采购经理审批", "time": "当前节点"},
             ],
         }),
    dict(approval_no="AP-2026-0813-005", approval_type="排产变更", title="NT-B班次调整：夜班产能提升",
         priority="普通", applicant="赵敏", applicant_role="计划员",
         submitted_at=datetime(2026, 8, 13, 11, 8), affect_lines="NT-B 南通B线",
         expect_effect_time="2026-08-18", risk_level="低风险", related_agent="Scheduler-Agent v2.4",
         need_countersign=False, status="pending",
         detail={
             "reason": "NT-B线8月下旬订单集中，白班产能不足，建议18日起增开夜班，日产能从240TEU提升至300TEU。",
             "plan_compare": {"original": "仅白班，8月底前需外协50TEU", "new": "白班+夜班，无需外协"},
             "impacts": [
                 {"type": "产能影响", "content": "日产能+60TEU，8月排产余量增加"},
                 {"type": "成本影响", "content": "夜班津贴增加约¥3.2万/月，低于外协成本"},
                 {"type": "交期影响", "content": "DFNT-2026-156-DS 交付提前2天"},
             ],
             "attachments": [],
             "timeline": [
                 {"node": "赵敏（计划员）提交审批", "time": "2026-08-13 11:08"},
                 {"node": "待生产部长审批", "time": "当前节点"},
             ],
         }),
    dict(approval_no="AP-2026-0812-004", approval_type="成本分摊", title="共享模具成本按订单量分摊规则调整",
         priority="普通", applicant="孙丽", applicant_role="财务专员",
         submitted_at=datetime(2026, 8, 12, 14, 30), affect_lines="全部产线",
         expect_effect_time="2026-09-01", risk_level="低风险", related_agent="Cost-Agent v1.2",
         need_countersign=True, status="pending",
         detail={
             "reason": "原按工时分摊共享模具折旧导致小批量工令成本偏差>8%，建议改为按订单量分摊。",
             "plan_compare": {"original": "按报工工时分摊（小批量工令偏态严重）",
                              "new": "按订单台数分摊（偏差降至<3%）"},
             "impacts": [
                 {"type": "成本影响", "content": "样箱/小批量工令成本下降约5%，大批量工令成本上升约1%"},
                 {"type": "合规影响", "content": "需财务经理+生产部长双签后生效"},
             ],
             "attachments": ["成本分摊模拟测算.xlsx"],
             "timeline": [
                 {"node": "孙丽（财务专员）提交规则调整", "time": "2026-08-12 14:30"},
                 {"node": "待财务经理+生产部长双签", "time": "当前节点"},
             ],
         }),
    dict(approval_no="AP-2026-0814-006", approval_type="排产变更", title="DFQD-2026-285-DS 提前2天投产",
         priority="高优先级", applicant="李计划", applicant_role="计划员",
         submitted_at=datetime(2026, 8, 14, 9, 30), affect_lines="QD-D 特箱线",
         expect_effect_time="2026-09-01", risk_level="中风险", related_agent="Scheduler-Agent v2.4",
         need_countersign=False, status="pending",
         detail={
             "reason": "客户要求提前交付，需将原计划9月3日的订单提前2天投产。",
             "plan_compare": {"original": "9月3日 08:00 启动，标准双班生产",
                              "new": "9月1日 08:00 启动，增加1个晚班补齐产能"},
             "impacts": [
                 {"type": "产能影响", "content": "焊接线A、装配线B需临时调整排班"},
                 {"type": "成本影响", "content": "加班费用增加，可能影响下周保养窗口"},
             ],
             "attachments": [],
             "timeline": [
                 {"node": "李计划提交审批", "time": "2026-08-14 09:30"},
                 {"node": "待审批", "time": "当前节点"},
             ],
         }),
    dict(approval_no="AP-2026-0814-007", approval_type="紧急维修", title="焊接机器人送丝异常维修工单",
         priority="高优先级", applicant="王设备", applicant_role="设备主管",
         submitted_at=datetime(2026, 8, 14, 10, 15), affect_lines="QD-D 焊接工段",
         expect_effect_time="立即", risk_level="高风险", related_agent="Device-Agent v1.8",
         need_countersign=False, status="pending",
         detail={
             "reason": "送丝机构磨损导致焊缝成型不良，质量Agent检出3批次气孔缺陷，需停机检修。",
             "plan_compare": {"original": "继续带病运行至周末", "new": "今日下午停机4小时检修"},
             "impacts": [{"type": "产能影响", "content": "当日减产约12台当量"}],
             "attachments": [],
             "timeline": [{"node": "王设备提交工单", "time": "2026-08-14 10:15"},
                          {"node": "待维修班组长接单", "time": "当前节点"}],
         }),
    dict(approval_no="AP-2026-0814-008", approval_type="样箱插单", title="样箱插单 - Ener C+ 2台",
         priority="普通", applicant="张业务", applicant_role="业务经理",
         submitted_at=datetime(2026, 8, 14, 11, 0), affect_lines="QD-D 特箱线",
         expect_effect_time="2026-08-18", risk_level="低风险", related_agent="Scheduler-Agent v2.4",
         need_countersign=False, status="pending",
         detail={
             "reason": "移动端现场接单转入：客户Enercore现场确认2台Ener C+样箱，8月18日前交付。",
             "plan_compare": {"original": "样箱未排入", "new": "插入8/14白班空位"},
             "impacts": [{"type": "产能影响", "content": "占用当日约4%产能"}],
             "attachments": [],
             "timeline": [{"node": "张业务（移动端）提交", "time": "2026-08-14 11:00"},
                          {"node": "待计划员确认", "time": "当前节点"}],
         }),
]
APPROVED_APPROVALS = [
    dict(approval_no="AP-2026-0811-002", approval_type="采购申请", title="木地板补充采购（300箱当量）",
         priority="普通", applicant="陈晨", applicant_role="采购专员",
         submitted_at=datetime(2026, 8, 11, 10, 0), affect_lines="QD-D",
         expect_effect_time="2026-08-25", risk_level="低风险", related_agent="SupplyChain-Agent v1.5",
         need_countersign=False, status="approved",
         detail={"reason": "木地板安全库存补足", "plan_compare": {"original": "-", "new": "补充采购300箱当量"},
                 "impacts": [], "attachments": [], "timeline": [{"node": "已通过", "time": "2026-08-11 15:00"}]}),
    dict(approval_no="AP-2026-0810-001", approval_type="排产变更", title="8月上旬排产计划（v3）生效",
         priority="高优先级", applicant="李明", applicant_role="计划员",
         submitted_at=datetime(2026, 8, 10, 9, 0), affect_lines="QD-D",
         expect_effect_time="2026-08-10", risk_level="中风险", related_agent="Scheduler-Agent v2.4",
         need_countersign=True, status="approved",
         detail={"reason": "月度排产计划审批", "plan_compare": {"original": "v2", "new": "v3 微调2个工令"},
                 "impacts": [], "attachments": [], "timeline": [{"node": "已通过", "time": "2026-08-10 14:00"}]}),
]


def _ensure_system(db: Session) -> None:
    """确保系统管理账号、角色、默认按钮权限与默认菜单存在（每次启动执行，幂等）"""
    if not db.query(User).filter(User.username == "admin").first():
        db.add(User(username="admin", display_name="系统管理员", role="管理员",
                    phone="13800000000"))
    # 播种角色（内置 + 物料管理员）
    from .permissions import BUILTIN_ROLES, DEFAULT_MENUS
    from .models import Role, RoleMenu
    for r in BUILTIN_ROLES:
        if not db.query(Role).filter(Role.name == r).first():
            db.add(Role(name=r,
                        description="负责物料信息维护" if r == "物料管理员" else "内置角色",
                        is_builtin=True))
    # 播种角色默认按钮权限
    for role, codes in DEFAULT_PERMS.items():
        if not db.query(RolePermission).filter(RolePermission.role == role).first():
            for c in codes:
                db.add(RolePermission(role=role, perm_code=c))
    # 播种角色默认菜单
    for role, menus in DEFAULT_MENUS.items():
        if not db.query(RoleMenu).filter(RoleMenu.role == role).first():
            for m in menus:
                db.add(RoleMenu(role=role, menu_code=m))
    db.commit()


def seed(db: Session) -> None:
    _ensure_system(db)
    if db.query(Factory).count() > 0:
        return

    for code, name in FACTORIES:
        db.add(Factory(factory_code=code, factory_name=name))
    for code, name, fc, lt, cap, scap, sunits in LINES:
        db.add(ProductionLine(line_code=code, line_name=name, factory_code=fc,
                              line_type=lt, daily_teu_capacity=cap,
                              storage_capacity=scap, storage_units=sunits))
    for row in BOX_TYPES:
        db.add(BoxType(code=row[0], name=row[1], category=row[2], daily_capacity_min=row[3],
                       daily_capacity_max=row[4], daily_capacity_std=row[5],
                       teu_factor=row[6], cteu_factor=row[7]))
    db.flush()  # autoflush=False：先落库，后续 _mk_plan 才能查到基础数据

    seq = 1
    for wo, cust, box, qty, s, e, st, ot, loc, remark in AUG_ORDERS:
        _mk_plan(db, seq, "QD-D", wo, cust, box, qty, s, e, st, ot, loc, remark)
        seq += 1
    for wo, cust, box, qty, s, e, st, ot, loc, remark in SEP_ORDERS:
        _mk_plan(db, seq, "QD-D", wo, cust, box, qty, s, e, st, ot, loc, remark)
        seq += 1
    for wo, cust, box, qty, s, e, st, ot, loc, remark in OCT_ORDERS:
        _mk_plan(db, seq, "QD-D", wo, cust, box, qty, s, e, st, ot, loc, remark)
        seq += 1
    for line, wo, cust, box, qty, s, e, st in OTHER_LINE_ORDERS:
        _mk_plan(db, seq, line, wo, cust, box, qty, s, e, st)
        seq += 1

    # 月度计划产能目标（TEU）
    aug_scheduled = (db.query(ScheduleDaily)
                     .filter(ScheduleDaily.line_code == "QD-D",
                             ScheduleDaily.schedule_date >= date(2026, 8, 1),
                             ScheduleDaily.schedule_date <= date(2026, 8, 31)))
    aug_teu = sum(r.teu or 0 for r in aug_scheduled)
    for month, teu in [("2026-08", max(aug_teu + 616, 3000)), ("2026-09", 3600), ("2026-10", 3400)]:
        db.add(MonthlyPlanTarget(line_code="QD-D", plan_month=month, plan_teu=teu))
    for line in ["SH-A", "NT-A", "NT-B", "LYG-A"]:
        db.add(MonthlyPlanTarget(line_code=line, plan_month="2026-08", plan_teu=4200))

    for d in DEVICES:
        db.add(Device(device_id=d[0], name=d[1], line_code=d[2], health=d[3],
                      status=d[4], rul_hours=d[5], rul_note=d[6]))
    for a in ALERTS:
        db.add(Alert(alert_time=a[0], source_agent=a[1], level=a[2], message=a[3], status=a[4]))
    _seed_materials(db)

    for a in APPROVALS + APPROVED_APPROVALS:
        db.add(Approval(**a))

    users = [
        ("zhang", "张业务", "业务经理", "13800000001"),
        ("liji", "李计划", "计划员", "13800000002"),
        ("wang", "王设备", "设备主管", "13800000003"),
        ("chen", "陈采购", "采购专员", "13800000004"),
        ("sun", "孙财务", "财务专员", "13800000005"),
        ("zhu", "张主管", "生产主管", "13800000006"),
    ]
    for u, n, r, p in users:
        db.add(User(username=u, display_name=n, role=r, phone=p))

    # 意向订单示例
    db.add(IntentionOrder(
        intention_id="IO-2026-0813-001", source="mobile",
        input_text="客户要200台20GP，10月底要，能排上吗", box_type="20GP", quantity=200,
        delivery_date=date(2026, 10, 31), delivery_location="上海", customer="东方国际",
        teu=200, schedule_analysis={}, status="confirmed", created_by="张业务",
        confirmed_at=datetime(2026, 8, 13, 15, 40)))
    db.add(IntentionOrder(
        intention_id="IO-2026-0814-001", source="mobile",
        input_text="意向新订单，Ener C+ 50台，急单，9月15日前交付上海", box_type="Ener C+",
        quantity=50, delivery_date=date(2026, 9, 15), delivery_location="上海", customer="Enercore",
        teu=100, schedule_analysis={}, status="pending", created_by="张业务"))

    notis = [
        ("张业务", "意向订单已确认", "IO-2026-0813-001 已由计划员确认排产（10/19~10/20 生产）", "排产"),
        ("张业务", "交期预警", "Ener C+ 50台急单：当前9月中旬产能紧张，建议提前确认", "预警"),
        ("张业务", "排产变更通知", "DFQD-2026-283-DS 排产已获审批生效（8/17~8/24）", "排产"),
        ("李计划", "新意向订单待处理", "张业务提交 Ener C+ 50台意向订单，请及时排产", "订单"),
    ]
    for u, t, c, ty in notis:
        db.add(Notification(user_name=u, title=t, content=c, ntype=ty))

    db.commit()
