"""排产工作台接口：排产计划 CRUD / 日历 / 产能汇总 / 智能排产 / what-if"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (Approval, BoxType, ScheduleDaily, SchedulePlan,
                      WorkCalendarDay)
from ..permissions import get_current_group, get_current_perms, require_perm
from ..services import planning_engine as engine
from ..services.calendar_util import workdays_between

router = APIRouter(prefix="/planning", tags=["planning"])

STATUS_CN = {"draft": "草稿", "pending_approval": "待审批", "confirmed": "已确认",
             "cancelled": "已取消", "completed": "已完成"}

# 产线 -> 所属工厂代码
LINE_FACTORY = {"PD-D": "SHPD", "BS-A": "SHBS", "JS-A": "SHJS", "JS-B": "SHJS", "FX-A": "SHFX"}


def _plan_dict(p: SchedulePlan, with_daily: bool = False) -> dict:
    d = {
        "id": p.id, "plan_id": p.plan_id, "plan_month": p.plan_month,
        "line_code": p.line_code, "work_order_no": p.work_order_no,
        "order_confirm_no": p.order_confirm_no, "contract_no": p.contract_no,
        "customer": p.customer, "box_type": p.box_type, "quantity": p.quantity,
        "teu": p.teu, "cteu": p.cteu, "production_deadline": p.production_deadline,
        "delivery_status": p.delivery_status, "order_source": p.order_source,
        "trade_type": p.trade_type, "delivery_location": p.delivery_location,
        "remark": p.remark, "daily_capacity": p.daily_capacity,
        "daily_planned_qty": p.daily_planned_qty,
        "start_date": p.start_date.isoformat() if p.start_date else None,
        "end_date": p.end_date.isoformat() if p.end_date else None,
        "order_type": p.order_type, "status": p.status, "status_cn": STATUS_CN.get(p.status, p.status),
        "version": p.version, "source": p.source, "created_by": p.created_by,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }
    if with_daily:
        pass
    return d


@router.get("/schedule")
def get_schedule(line_code: str = "PD-D", month: str = "2026-08",
                 group: str = Depends(get_current_group), db: Session = Depends(get_db)):
    year, mon = int(month[:4]), int(month[5:7])
    orders = (db.query(SchedulePlan)
              .filter(SchedulePlan.line_code == line_code, SchedulePlan.plan_month == month)
              .order_by(SchedulePlan.start_date).all())
    # 审批人：只能查看已排待审批的工令
    if group == "approver":
        orders = [o for o in orders if o.status == "pending_approval"]
    daily_map: dict[str, list] = {}
    rows = (db.query(ScheduleDaily)
            .filter(ScheduleDaily.line_code == line_code,
                    ScheduleDaily.schedule_date >= date(year, mon, 1),
                    ScheduleDaily.schedule_date <= (date(year, mon + 1, 1) - timedelta(days=1)) if mon < 12 else date(year, 12, 31))
            .all())
    for r in rows:
        daily_map.setdefault(r.schedule_date.isoformat(), []).append(
            {"work_order_no": r.work_order_no, "qty": r.planned_qty, "teu": r.teu})
    calendar = engine.daily_utilization(db, line_code, year, mon)
    for day in calendar:
        day["items"] = daily_map.get(day["date"], [])
    return {
        "line_code": line_code, "month": month,
        "summary": engine.capacity_summary(db, line_code, year, mon),
        "pending_approvals": db.query(Approval).filter(
            Approval.status == "pending", Approval.approval_type.in_(["排产变更", "样箱插单"])).count(),
        "orders": [_plan_dict(o) for o in orders],
        "calendar": calendar,
    }


class WorkOrderIn(BaseModel):
    work_order_no: str
    line_code: str = "PD-D"
    customer: str
    box_type: str
    quantity: int
    start_date: str
    end_date: str
    order_confirm_no: str = ""
    contract_no: str = ""
    production_deadline: str = "按时"
    order_source: str = "自接单"
    trade_type: str = "外贸"
    delivery_location: str = ""
    remark: str = ""
    daily_capacity: int | None = None
    daily_planned_qty: int | None = None
    order_type: str = "批量"
    status: str = "draft"
    source: str = "manual"
    created_by: str = "李计划"


def _gen_work_order_no(db: Session, line_code: str) -> str:
    """按产线对应工厂生成工令号：{工厂}-2026-{序号:03d}-DS"""
    factory = LINE_FACTORY.get(line_code, "SHPD")
    prefix = f"{factory}-2026-"
    n = 305 + db.query(SchedulePlan).filter(SchedulePlan.work_order_no.like(f"{prefix}%")).count()
    return f"{prefix}{n:03d}-DS"


@router.post("/manual")
def create_order(body: WorkOrderIn, _: str = Depends(require_perm("workorder.add")),
                 db: Session = Depends(get_db)):
    box = db.query(BoxType).filter(BoxType.code == body.box_type).first()
    if not box:
        raise HTTPException(400, f"未知箱型：{body.box_type}")
    s, e = date.fromisoformat(body.start_date), date.fromisoformat(body.end_date)
    if e < s:
        raise HTTPException(400, "结束日期不能早于开始日期")
    overrides = engine.get_overrides(db, body.line_code)
    wds = workdays_between(s, e, overrides)
    if not wds:
        raise HTTPException(400, "排产区间内没有工作日")

    daily_qty = body.daily_planned_qty or max(body.quantity // len(wds), 1)

    wo = body.work_order_no or _gen_work_order_no(db, body.line_code)
    plan = SchedulePlan(
        plan_id=f"PLAN-{uuid.uuid4().hex[:12]}", plan_month=f"{s.year:04d}-{s.month:02d}",
        factory_code=LINE_FACTORY.get(body.line_code, "SHPD"), line_code=body.line_code, work_order_no=wo,
        order_confirm_no=body.order_confirm_no, contract_no=body.contract_no,
        customer=body.customer, box_type=body.box_type, quantity=body.quantity,
        teu=int(body.quantity * float(box.teu_factor)),
        cteu=int(body.quantity * float(box.cteu_factor)),
        production_deadline=body.production_deadline, order_source=body.order_source,
        trade_type=body.trade_type, delivery_location=body.delivery_location,
        remark=body.remark, daily_capacity=body.daily_capacity or box.daily_capacity_std,
        daily_planned_qty=daily_qty, start_date=s, end_date=e, order_type=body.order_type,
        status=body.status, source=body.source, created_by=body.created_by,
    )
    db.add(plan)
    db.flush()
    engine_apply = []
    remaining = body.quantity
    for d in wds:
        q = min(daily_qty, remaining)
        if q <= 0:
            break
        engine_apply.append((d, q))
        remaining -= q
    for d, q in engine_apply:
        db.add(ScheduleDaily(plan_id=plan.plan_id, work_order_no=wo, line_code=body.line_code,
                             schedule_date=d, planned_qty=q,
                             teu=int(q * float(box.teu_factor)), is_workday=True))
    db.commit()
    return {"message": "保存成功", "plan": _plan_dict(plan)}


@router.put("/schedule/{plan_id}")
def update_order(plan_id: int, body: WorkOrderIn, _: str = Depends(require_perm("workorder.edit")),
                 db: Session = Depends(get_db)):
    plan = db.query(SchedulePlan).filter(SchedulePlan.id == plan_id).first()
    if not plan:
        raise HTTPException(404, "工令不存在")
    if plan.status != "draft":
        raise HTTPException(400, f"工令当前状态为「{STATUS_CN.get(plan.status, plan.status)}」，"
                                 "仅草稿工令可编辑")
    box = db.query(BoxType).filter(BoxType.code == body.box_type).first()
    s, e = date.fromisoformat(body.start_date), date.fromisoformat(body.end_date)
    plan.work_order_no = body.work_order_no or plan.work_order_no
    plan.customer = body.customer
    plan.box_type = body.box_type
    plan.quantity = body.quantity
    plan.teu = int(body.quantity * float(box.teu_factor))
    plan.cteu = int(body.quantity * float(box.cteu_factor))
    plan.start_date, plan.end_date = s, e
    plan.plan_month = f"{s.year:04d}-{s.month:02d}"
    plan.daily_capacity = body.daily_capacity or box.daily_capacity_std
    plan.daily_planned_qty = body.daily_planned_qty or max(body.quantity // max(len(workdays_between(s, e, engine.get_overrides(db, plan.line_code))), 1), 1)
    plan.order_type = body.order_type
    plan.delivery_location = body.delivery_location
    plan.remark = body.remark
    plan.version += 1
    plan.updated_at = datetime.now()

    db.query(ScheduleDaily).filter(ScheduleDaily.plan_id == plan.plan_id).delete()
    wds = workdays_between(s, e, engine.get_overrides(db, plan.line_code))
    remaining, daily = plan.quantity, plan.daily_planned_qty
    for d in wds:
        q = min(daily, remaining)
        if q <= 0:
            break
        remaining -= q
        db.add(ScheduleDaily(plan_id=plan.plan_id, work_order_no=plan.work_order_no,
                             line_code=plan.line_code, schedule_date=d, planned_qty=q,
                             teu=int(q * float(box.teu_factor)), is_workday=True))
    db.commit()
    return {"message": "更新成功", "plan": _plan_dict(plan)}


@router.delete("/schedule/{plan_id}")
def delete_order(plan_id: int, _: str = Depends(require_perm("workorder.delete")),
                 db: Session = Depends(get_db)):
    plan = db.query(SchedulePlan).filter(SchedulePlan.id == plan_id).first()
    if not plan:
        raise HTTPException(404, "工令不存在")
    if plan.status != "draft":
        raise HTTPException(400, f"工令当前状态为「{STATUS_CN.get(plan.status, plan.status)}」，"
                                 "仅草稿工令可删除")
    db.query(ScheduleDaily).filter(ScheduleDaily.plan_id == plan.plan_id).delete()
    db.delete(plan)
    db.commit()
    return {"message": "已删除"}


@router.post("/schedule/{plan_id}/confirm")
def confirm_order(plan_id: int, operator: str = "李计划",
                  _: str = Depends(require_perm("planning.schedule")),
                  db: Session = Depends(get_db)):
    """确认排产 → 生成审批单（L2 人工确认后生效，仅拥有排产权限者操作）"""
    plan = db.query(SchedulePlan).filter(SchedulePlan.id == plan_id).first()
    if not plan:
        raise HTTPException(404, "工令不存在")
    if plan.status != "draft":
        raise HTTPException(400, f"工令当前状态为「{STATUS_CN.get(plan.status, plan.status)}」，"
                                 "仅草稿工令可确认排产，避免重复进入审批流程")
    plan.status = "pending_approval"
    plan.version += 1
    db.flush()
    base = f"AP-{datetime.now().strftime('%Y-%m%d')}-{plan.id:03d}"
    no = base
    seq = 1
    while db.query(Approval).filter(Approval.approval_no == no).first():
        seq += 1
        no = f"{base}-{seq}"
    db.add(Approval(
        approval_no=no, approval_type="排产变更",
        title=f"排产确认：{plan.work_order_no}（{plan.box_type} × {plan.quantity}台）",
        priority="普通", applicant=operator, applicant_role="计划员",
        affect_lines=plan.line_code, expect_effect_time=plan.start_date.isoformat() if plan.start_date else "",
        risk_level="中风险", related_agent="Scheduler-Agent v2.4", need_countersign=True,
        target_type="schedule_plan", target_id=str(plan.id), status="pending",
        detail={
            "reason": f"工令 {plan.work_order_no} 排产方案（{plan.start_date} ~ {plan.end_date}）提交审批，审批通过后写入正式排产计划。",
            "plan_compare": {"original": "（新增排产）", "new": f"{plan.start_date} ~ {plan.end_date}，日排产 {plan.daily_planned_qty} 台"},
            "impacts": [{"type": "产能影响", "content": f"占用产能 {plan.teu} TEU"}],
            "attachments": [], "timeline": [
                {"node": f"{operator}（计划员）提交审批", "time": datetime.now().strftime("%Y-%m-%d %H:%M")},
                {"node": "待生产部长审批", "time": "当前节点"}],
        }))
    db.commit()
    return {"message": "已提交审批", "approval_no": no}


@router.get("/conflicts")
def conflicts(line_code: str = "PD-D", month: str = "2026-08", db: Session = Depends(get_db)):
    year, mon = int(month[:4]), int(month[5:7])
    days = engine.daily_utilization(db, line_code, year, mon)
    return [{"date": d["date"], "utilization": d["utilization"], "booked_teu": d["booked_teu"],
             "orders": d["orders"]} for d in days if d["status"] == "conflict"]


@router.get("/gantt-data")
def gantt_data(line_code: str = "PD-D", month: str = "2026-08",
               group: str = Depends(get_current_group), db: Session = Depends(get_db)):
    orders = (db.query(SchedulePlan)
              .filter(SchedulePlan.line_code == line_code, SchedulePlan.plan_month == month,
                      SchedulePlan.start_date.isnot(None))
              .order_by(SchedulePlan.start_date).all())
    # 审批人：只能查看已排待审批的工令
    if group == "approver":
        orders = [o for o in orders if o.status == "pending_approval"]
    colors = {"confirmed": "#06b6d4", "pending_approval": "#f59e0b",
              "draft": "#38bdf8", "completed": "#10b981"}
    return [{"work_order_no": o.work_order_no, "customer": o.customer, "box_type": o.box_type,
             "start": o.start_date.isoformat(), "end": o.end_date.isoformat(),
             "quantity": o.quantity, "teu": o.teu, "status": o.status,
             "color": colors.get(o.status, "#0891b2")}
            for o in orders]


@router.get("/calendar")
def get_calendar(line_code: str = "PD-D", month: str = "2026-08", db: Session = Depends(get_db)):
    year, mon = int(month[:4]), int(month[5:7])
    days = engine.daily_utilization(db, line_code, year, mon)
    return [{"date": d["date"], "day": d["day"], "is_workday": d["is_workday"],
             "hours": d["hours"], "day_of_week": d["day_of_week"], "note": d["note"],
             "daily_capacity": d.get("daily_capacity", 0), "booked_teu": d["booked_teu"],
             "utilization": d["utilization"], "status": d["status"], "items": d["orders"]}
            for d in days]


class CalendarUpdate(BaseModel):
    date: str
    is_workday: bool
    hours: int = 0
    note: str = ""
    daily_capacity: int = 0


@router.put("/calendar")
def update_calendar(line_code: str, body: CalendarUpdate,
                    _: str = Depends(require_perm("planning.calendar")),
                    db: Session = Depends(get_db)):
    d = date.fromisoformat(body.date)
    row = (db.query(WorkCalendarDay)
           .filter(WorkCalendarDay.line_code == line_code, WorkCalendarDay.cal_date == d).first())
    if row:
        row.is_workday, row.planned_hours, row.note = body.is_workday, body.hours, body.note
        row.daily_capacity = body.daily_capacity
    else:
        db.add(WorkCalendarDay(line_code=line_code, cal_date=d, is_workday=body.is_workday,
                               planned_hours=body.hours, note=body.note,
                               daily_capacity=body.daily_capacity))
    db.commit()
    return {"message": "日历已更新"}


class CalendarBatchItem(BaseModel):
    date: str
    daily_capacity: int = 0    # 0=休息日，>0=当日日产能 TEU
    note: str = ""


@router.post("/calendar/batch")
def update_calendar_batch(line_code: str, body: list[CalendarBatchItem],
                          _: str = Depends(require_perm("planning.calendar")),
                          db: Session = Depends(get_db)):
    """批量保存产线排班配置：每日日产能（0=休息，否则需填写产能）。"""
    saved = 0
    days = db.query(WorkCalendarDay).filter(WorkCalendarDay.line_code == line_code).all()
    by_date = {r.cal_date: r for r in days}
    for it in body:
        d = date.fromisoformat(it.date)
        cap = max(int(it.daily_capacity), 0)
        row = by_date.get(d)
        if row:
            row.is_workday = cap > 0
            row.planned_hours = 8 if cap > 0 else 0
            row.daily_capacity = cap
            row.note = it.note
        else:
            db.add(WorkCalendarDay(line_code=line_code, cal_date=d, is_workday=cap > 0,
                                   planned_hours=8 if cap > 0 else 0,
                                   daily_capacity=cap, note=it.note))
        saved += 1
    db.commit()
    return {"message": f"已保存 {saved} 天排班配置"}


@router.get("/capacity-summary")
def capacity(line_code: str = "PD-D", month: str = "2026-08", db: Session = Depends(get_db)):
    return engine.capacity_summary(db, line_code, int(month[:4]), int(month[5:7]))


# ---------- 甘特按天矩阵（按天统计，支持手工输入每日产能） ----------
@router.get("/gantt-days")
def gantt_days(line_code: str = "PD-D", month: str = "2026-08",
               group: str = Depends(get_current_group), db: Session = Depends(get_db)):
    """返回当月每天明细 + 每个工令的按日排产量矩阵 + 每日产能合计"""
    year, mon = int(month[:4]), int(month[5:7])
    last_day = (date(year, mon + 1, 1) - timedelta(days=1)) if mon < 12 else date(year, 12, 31)
    orders = (db.query(SchedulePlan)
              .filter(SchedulePlan.line_code == line_code, SchedulePlan.plan_month == month)
              .order_by(SchedulePlan.start_date).all())
    # 审批人：只能查看已排待审批的工令
    if group == "approver":
        orders = [o for o in orders if o.status == "pending_approval"]
    rows = (db.query(ScheduleDaily)
            .filter(ScheduleDaily.line_code == line_code,
                    ScheduleDaily.schedule_date >= date(year, mon, 1),
                    ScheduleDaily.schedule_date <= last_day).all())

    order_daily: dict[str, dict[str, int]] = {}
    daily_total: dict[str, int] = {}
    for r in rows:
        k = r.schedule_date.isoformat()
        order_daily.setdefault(r.work_order_no, {})[k] = r.planned_qty
        daily_total[k] = daily_total.get(k, 0) + r.planned_qty

    colors = {"confirmed": "#06b6d4", "pending_approval": "#f59e0b",
              "draft": "#38bdf8", "completed": "#10b981", "cancelled": "#94a3b8"}
    days = []
    d0 = date(year, mon, 1)
    dow_cn = ["一", "二", "三", "四", "五", "六", "日"]
    for i in range((last_day - d0).days + 1):
        d = d0 + timedelta(days=i)
        cap = engine.day_capacity(db, line_code, d)
        days.append({"date": d.isoformat(), "day": d.day, "dow": dow_cn[d.weekday()],
                     "is_weekend": d.weekday() >= 5, "daily_capacity": cap})
    return {
        "days": days,
        "orders": [{
            "plan_id": o.plan_id, "work_order_no": o.work_order_no,
            "customer": o.customer, "box_type": o.box_type, "quantity": o.quantity,
            "teu": o.teu, "start": o.start_date.isoformat() if o.start_date else None,
            "end": o.end_date.isoformat() if o.end_date else None,
            "status": o.status, "status_cn": STATUS_CN.get(o.status, o.status),
            "color": colors.get(o.status, "#0891b2"),
            "daily": order_daily.get(o.work_order_no, {}),
        } for o in orders],
        "daily_total": daily_total,
    }


class GanttDailyItem(BaseModel):
    work_order_no: str
    daily: dict[str, int]   # {"2026-08-12": 80, ...}


@router.post("/gantt-days")
def save_gantt_days(line_code: str = "PD-D", items: list[GanttDailyItem] = None,
                    _: str = Depends(require_perm("planning.schedule")),
                    db: Session = Depends(get_db)):
    """保存甘特按天矩阵：逐工令落库每日排产量（0 表示清除该日）。
    校验：当天所有工令排产量合计不得超过当日排班配置的日产能（0=休息日不可排产）。"""
    if items is None:
        items = []

    # 第一遍：汇总每个日期所有工令的排产量，用于日产能校验
    day_totals: dict[str, int] = {}
    for it in items:
        for dstr, qty in it.daily.items():
            if qty > 0:
                day_totals[dstr] = day_totals.get(dstr, 0) + int(qty)
    for dstr, total in day_totals.items():
        cap = engine.day_capacity(db, line_code, date.fromisoformat(dstr))
        if cap <= 0:
            raise HTTPException(400, f"{dstr} 为休息日（日产能 0），不可排产")
        if total > cap:
            raise HTTPException(400, f"{dstr} 排产量合计 {total} TEU 超过当日日产能 {cap} TEU")

    saved = 0
    for it in items:
        plan = db.query(SchedulePlan).filter(
            SchedulePlan.line_code == line_code,
            SchedulePlan.work_order_no == it.work_order_no).first()
        if not plan:
            continue
        # 待审批/已确认/已完成等非草稿工令不可修改按天排产数量
        if plan.status != "draft":
            continue
        # 校验：该工令所有排产日数量总和不得超过工令总数量
        wo_total = sum(int(q) for q in it.daily.values() if int(q) > 0)
        if wo_total > plan.quantity:
            raise HTTPException(400, f"工令 {plan.work_order_no} 排产合计 {wo_total} 台超过工令总数量 {plan.quantity} 台")
        box = db.query(BoxType).filter(BoxType.code == plan.box_type).first()
        if not box:
            continue
        dates = sorted(it.daily.keys())
        for dstr, qty in it.daily.items():
            dd = date.fromisoformat(dstr)
            row = (db.query(ScheduleDaily)
                   .filter(ScheduleDaily.plan_id == plan.plan_id,
                           ScheduleDaily.schedule_date == dd).first())
            if qty <= 0:
                if row:
                    db.delete(row)
                continue
            if row:
                row.planned_qty = qty
                row.teu = int(qty * float(box.teu_factor))
            else:
                db.add(ScheduleDaily(plan_id=plan.plan_id, work_order_no=plan.work_order_no,
                                     line_code=line_code, schedule_date=dd, planned_qty=qty,
                                     teu=int(qty * float(box.teu_factor)),
                                     day_of_week=["一", "二", "三", "四", "五", "六", "日"][dd.weekday()],
                                     is_workday=True))
        if dates:
            plan.start_date = date.fromisoformat(dates[0])
            plan.end_date = date.fromisoformat(dates[-1])
            plan.daily_planned_qty = max(it.daily.values())
            plan.version += 1
            plan.updated_at = datetime.now()
        saved += 1
    db.commit()
    return {"message": "已保存按天排产", "saved": saved}


class SmartPlanReq(BaseModel):
    line_code: str = "PD-D"
    month: str = "2026-08"
    apply: bool = False
    operator: str = "李计划"
    work_order_no: str | None = None          # 单选工令排产
    proposals: list[dict] | None = None       # 前端手工调整后的建议（apply 时使用）


@router.post("/smart")
def smart(body: SmartPlanReq, perms: set[str] | None = Depends(get_current_perms),
          db: Session = Depends(get_db)):
    # 智能排产落库（apply=True）需拥有智能排产权限
    if body.apply and perms is not None and "planning.smart" not in perms:
        raise HTTPException(403, "无权限执行该操作")
    if body.apply:
        # 若前端传入了手工调整后的建议，则直接应用之
        if body.proposals is not None:
            count = engine.apply_smart_plan(db, body.line_code, body.proposals, body.operator)
            return {"applied": True, "applied_count": count, "message": "已应用调整后的建议"}
        result = engine.smart_plan(db, body.line_code, int(body.month[:4]), int(body.month[5:7]))
        if result["proposals"]:
            engine.apply_smart_plan(db, body.line_code, result["proposals"], body.operator)
            result["applied"] = True
        return result
    return engine.smart_plan(db, body.line_code, int(body.month[:4]), int(body.month[5:7]),
                             work_order_no=body.work_order_no)


class AdjustAnalyzeReq(BaseModel):
    line_code: str = "PD-D"
    work_order_no: str
    daily_schedule: list[dict] = []           # [{"date": "2026-08-12", "qty": 80}, ...]
    delivery_date: str | None = None


@router.post("/smart/adjust-analyze")
def smart_adjust_analyze(body: AdjustAnalyzeReq, db: Session = Depends(get_db)):
    """对手工调整后的每日排产方案给出智能建议（利用率/冲突/交期/物料）"""
    return engine.analyze_adjusted(db, body.line_code, body.work_order_no,
                                   body.daily_schedule, body.delivery_date)


class WhatIfReq(BaseModel):
    box_type: str
    quantity: int
    delivery_date: str | None = None
    delivery_location: str | None = None
    line_code: str = "PD-D"


@router.post("/what-if")
def what_if(body: WhatIfReq, db: Session = Depends(get_db)):
    dd = date.fromisoformat(body.delivery_date) if body.delivery_date else date.today() + timedelta(days=30)
    return engine.feasibility_analysis(db, body.box_type, body.quantity, dd,
                                       body.line_code, body.delivery_location)


@router.get("/version-history")
def version_history(line_code: str = "PD-D", month: str = "2026-08", db: Session = Depends(get_db)):
    orders = (db.query(SchedulePlan)
              .filter(SchedulePlan.line_code == line_code, SchedulePlan.plan_month == month).all())
    return [{"work_order_no": o.work_order_no, "version": o.version, "status": o.status,
             "updated_at": o.updated_at.isoformat() if o.updated_at else None,
             "source": o.source, "created_by": o.created_by}
            for o in sorted(orders, key=lambda x: x.updated_at or datetime.now(), reverse=True)[:20]]
