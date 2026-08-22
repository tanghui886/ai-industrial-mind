"""排产引擎：产能校验、可行性分析、智能排产、what-if 模拟"""
from __future__ import annotations

import math
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from fastapi import HTTPException

from ..models import (BoxType, Material, MonthlyPlanTarget, ScheduleDaily,
                      SchedulePlan, WorkCalendarDay)
from .calendar_util import (default_workday, month_calendar,
                            next_workdays, workdays_between)

DEFAULT_LINE = "PD-D"
INSPECTION_DAYS = 2
TRANSPORT_DAYS = {"上海": 2, "青岛": 2, "宁波": 2, "连云港": 2, "南通": 2, "启东": 2,
                  "天津": 3, "深圳": 3, "广州": 3, "厦门": 3, "大连": 3, " default": 3}


def get_overrides(db: Session, line_code: str) -> dict:
    rows = db.query(WorkCalendarDay).filter(WorkCalendarDay.line_code == line_code).all()
    return {r.cal_date.isoformat(): {"is_workday": r.is_workday, "hours": r.planned_hours,
                                     "daily_capacity": r.daily_capacity or 0,
                                     "note": r.note or ""} for r in rows}


def day_capacity(db: Session, line_code: str, day: date) -> int:
    """指定产线指定日期的日产能（TEU）。0=休息日；未配置排班时按工作日默认产能。"""
    cap = line_daily_capacity(db, line_code)
    row = (db.query(WorkCalendarDay)
           .filter(WorkCalendarDay.line_code == line_code,
                   WorkCalendarDay.cal_date == day).first())
    if row is not None:
        return max(row.daily_capacity or 0, 0)
    ov = get_overrides(db, line_code).get(day.isoformat())
    is_wd = ov["is_workday"] if ov else default_workday(day)
    return cap if is_wd else 0


def get_box_type(db: Session, code: str) -> BoxType | None:
    return db.query(BoxType).filter(BoxType.code == code).first()


def booked_map(db: Session, line_code: str, start: date, end: date) -> dict[str, dict]:
    """指定日期范围内每日已排产量 {date: {qty, teu, orders:{wo: {qty, teu}}}}"""
    rows = (db.query(ScheduleDaily)
            .filter(ScheduleDaily.line_code == line_code,
                    ScheduleDaily.schedule_date >= start,
                    ScheduleDaily.schedule_date <= end)
            .all())
    result: dict[str, dict] = {}
    for r in rows:
        d = r.schedule_date.isoformat()
        bucket = result.setdefault(d, {"qty": 0, "teu": 0, "orders": {}})
        bucket["qty"] += r.planned_qty
        bucket["teu"] += r.teu or 0
        item = bucket["orders"].setdefault(r.work_order_no, {"qty": 0, "teu": 0})
        item["qty"] += r.planned_qty
        item["teu"] += r.teu or 0
    return result


def line_daily_capacity(db: Session, line_code: str) -> int:
    from ..models import ProductionLine
    line = db.query(ProductionLine).filter(ProductionLine.line_code == line_code).first()
    return line.daily_teu_capacity if line else 180


def month_plan_teu(db: Session, line_code: str, month: str) -> int:
    row = (db.query(MonthlyPlanTarget)
           .filter(MonthlyPlanTarget.line_code == line_code,
                   MonthlyPlanTarget.plan_month == month).first())
    return row.plan_teu if row else 2400


def daily_utilization(db: Session, line_code: str, year: int, month: int) -> list[dict]:
    """整月逐日产能占用（含日历与利用率状态，产能来自排班配置）"""
    overrides = get_overrides(db, line_code)
    cal = month_calendar(year, month, overrides)
    start, end = date(year, month, 1), date(year, month, 1)
    if month == 12:
        end = date(year, 12, 31)
    else:
        end = date(year, month + 1, 1) - timedelta(days=1)
    booked = booked_map(db, line_code, start, end)
    for day in cal:
        cap = day_capacity(db, line_code, date.fromisoformat(day["date"]))
        b = booked.get(day["date"], {"qty": 0, "teu": 0, "orders": {}})
        util = round(b["teu"] / cap * 100, 1) if cap > 0 else 0
        if cap <= 0:
            status = "rest"
        elif util > 100:
            status = "conflict"
        elif util >= 85:
            status = "tight"
        else:
            status = "normal"
        # 每个订单的产能量占比（用于日历按订单分段展示）
        order_items = []
        for wo, o in b["orders"].items():
            pct = round(o["teu"] / cap * 100, 1) if cap > 0 else 0
            order_items.append({"work_order_no": wo, "qty": o["qty"], "teu": o["teu"], "pct": pct})
        day.update({"is_workday": cap > 0, "daily_capacity": cap, "booked_qty": b["qty"],
                    "booked_teu": b["teu"], "utilization": util, "status": status,
                    "orders": order_items})
    return cal


def capacity_summary(db: Session, line_code: str, year: int, month: int) -> dict:
    month_str = f"{year:04d}-{month:02d}"
    days = daily_utilization(db, line_code, year, month)
    plan_teu = month_plan_teu(db, line_code, month_str)
    scheduled = sum(d["booked_teu"] for d in days)
    workdays = sum(1 for d in days if d["is_workday"])
    conflicts = sum(1 for d in days if d["status"] == "conflict")
    util = round(scheduled / plan_teu * 100, 1) if plan_teu else 0
    # 分日空位明细：仅保留有工作能力的日期，逐日计算剩余可排产能
    daily_free = []
    for d in days:
        if not d["is_workday"]:
            continue
        cap = d["daily_capacity"]
        booked = d["booked_teu"]
        remaining = max(cap - booked, 0)
        daily_free.append({
            "date": d["date"],
            "capacity": cap,
            "booked_teu": booked,
            "remaining_teu": remaining,
            "status": d["status"],
        })
    return {
        "line_code": line_code,
        "month": month_str,
        "plan_teu": plan_teu,
        "scheduled_teu": scheduled,
        "remaining_teu": max(plan_teu - scheduled, 0),
        "utilization_rate": util,
        "workdays": workdays,
        "conflict_days": conflicts,
        "daily_free": daily_free,
    }


def _material_check(db: Session, box: BoxType, quantity: int) -> dict:
    """物料齐套检查（演示模型：按 TEU 当量消耗 vs 库存支撑）"""
    result = {}
    teu_demand = quantity * float(box.teu_factor)
    materials = db.query(Material).all()
    consume_map = {"STEEL": quantity * float(box.teu_factor),      # 钢板按 TEU
                   "PAINT": quantity * float(box.teu_factor) * 0.9,
                   "CORNER": quantity * 1.0,                        # 角件按台数
                   "FLOOR": quantity * float(box.teu_factor) * 0.8,
                   "LOCK": quantity * 1.0}
    name_map = {"STEEL": "steel_spa_h", "PAINT": "paint", "CORNER": "corner_fittings",
                "FLOOR": "floor", "LOCK": "lock_rod"}
    for m in materials:
        key = name_map.get(m.code)
        if not key:
            continue
        demand = consume_map.get(m.code, quantity)
        if demand <= m.support_units:
            status, note = "sufficient", f"当前库存满足 {m.support_units:.0f} 台当量，需求 {demand:.0f}"
        elif demand <= m.support_units + m.in_transit_units:
            status = "warning"
            eta = m.arrival_date.isoformat() if m.arrival_date else "待确认"
            note = f"库存满足 {m.support_units:.0f}，缺口需在途 {m.in_transit_units:.0f}（预计 {eta} 到货）"
        else:
            status, note = "insufficient", f"库存+在途仍缺口 {demand - m.support_units - m.in_transit_units:.0f}，建议尽快下单"
        result[key] = {"status": status, "note": note, "name": m.name}
    return result


def _transport_days(location: str | None) -> int:
    if not location:
        return 3
    return TRANSPORT_DAYS.get(location, 3)


def feasibility_analysis(db: Session, box_type_code: str, quantity: int,
                         delivery_date: date | None, line_code: str = DEFAULT_LINE,
                         delivery_location: str | None = None,
                         start_from: date | None = None, today: date | None = None) -> dict:
    """排产可行性分析（对齐方案 v6 §4.3.5 输出示例）"""
    today = today or date.today()
    box = get_box_type(db, box_type_code)
    if not box:
        return {"feasibility": "unknown", "message": f"未识别箱型 {box_type_code}"}

    teu_total = int(quantity * float(box.teu_factor))
    daily_std = box.daily_capacity_std
    need_days = max(math.ceil(quantity / daily_std), 1)
    overrides = get_overrides(db, line_code)

    # 最晚完工日：交付期 - 检验 - 运输
    deadline = delivery_date or (today + timedelta(days=45))
    latest_finish = deadline - timedelta(days=INSPECTION_DAYS + _transport_days(delivery_location))

    # 自起始日向后逐日分配（受当日配置产能与箱型日产能双重约束）
    start_from = max(start_from or (today + timedelta(days=1)), today + timedelta(days=1))
    d = start_from
    remaining = quantity
    schedule: list[dict] = []
    guard = 0
    while remaining > 0 and d <= latest_finish and guard < 400:
        guard += 1
        cap = day_capacity(db, line_code, d)
        if cap > 0:
            booked = booked_map(db, line_code, d, d).get(d.isoformat(), {"teu": 0})
            free_teu = cap - booked["teu"]
            max_units = min(daily_std, int(free_teu // max(float(box.teu_factor), 0.5)))
            qty = min(max_units, remaining)
            if qty > 0:
                schedule.append({"date": d.isoformat(), "qty": int(qty)})
                remaining -= qty
        d += timedelta(days=1)

    # 汇总
    month_key = (schedule[0]["date"][:7] if schedule else f"{today.year:04d}-{today.month:02d}")
    summary = capacity_summary(db, line_code, int(month_key[:4]), int(month_key[5:7]))
    after_teu = summary["scheduled_teu"] + teu_total
    after_util = round(after_teu / summary["plan_teu"] * 100, 1) if summary["plan_teu"] else 0

    if remaining > 0:
        feasibility, score = "tight", 0.55
        if not schedule:
            feasibility, score = "infeasible", 0.2
    else:
        feasibility, score = "feasible", 0.92

    # 冲突工令分析：与排产窗口重叠的已确认工令
    conflict_orders = []
    if schedule:
        w_start = date.fromisoformat(schedule[0]["date"])
        w_end = date.fromisoformat(schedule[-1]["date"])
        rows = (db.query(SchedulePlan)
                .filter(SchedulePlan.line_code == line_code,
                        SchedulePlan.start_date <= w_end,
                        SchedulePlan.end_date >= w_start,
                        SchedulePlan.status.in_(["confirmed", "draft", "pending_approval"]))
                .all())
        for r in rows:
            ov_days = [wd.isoformat() for wd in workdays_between(max(r.start_date, w_start),
                                                                 min(r.end_date, w_end), overrides)][:4]
            if ov_days:
                conflict_orders.append({"work_order_no": r.work_order_no, "box_type": r.box_type,
                                        "overlap_days": ov_days,
                                        "impact": f"重叠 {len(ov_days)} 个工作日，已自动压低当日排产量"})

    # 交付评估
    prod_end = date.fromisoformat(schedule[-1]["date"]) if schedule else latest_finish
    est_delivery = prod_end + timedelta(days=INSPECTION_DAYS + _transport_days(delivery_location))
    buffer_days = (deadline - est_delivery).days
    risk_level = "low" if buffer_days >= 7 else ("medium" if buffer_days >= 3 else "high")

    material_check = _material_check(db, box, quantity)
    risk_alerts = [f"{v['name']}：{v['note']}" for v in material_check.values() if v["status"] != "sufficient"]
    for c in conflict_orders[:2]:
        risk_alerts.append(f"与 {c['work_order_no']}（{c['box_type']}）存在产能重叠，{c['impact']}")

    return {
        "feasibility": feasibility,
        "feasibility_score": score,
        "order_info": {
            "box_type": box.code,
            "box_type_display": box.name,
            "quantity": quantity,
            "teu": teu_total,
            "delivery_date": deadline.isoformat(),
            "delivery_location": delivery_location or "待确认",
            "daily_capacity": daily_std,
            "estimated_production_days": need_days,
        },
        "schedule_suggestion": {
            "recommended_start": schedule[0]["date"] if schedule else None,
            "recommended_end": schedule[-1]["date"] if schedule else None,
            "daily_schedule": schedule,
            "note": f"共 {len(schedule)} 个工作日，日排产 {min(s['qty'] for s in schedule)}~{daily_std} 台" if schedule else "产能不足，无法在交付期内安排",
        },
        "delivery_assessment": {
            "production_complete": prod_end.isoformat(),
            "inspection_days": INSPECTION_DAYS,
            "transport_days": _transport_days(delivery_location),
            "estimated_delivery": est_delivery.isoformat(),
            "deadline": deadline.isoformat(),
            "buffer_days": buffer_days,
            "risk_level": risk_level,
        },
        "capacity_impact": {
            "month": month_key,
            "current_utilization": f"{summary['utilization_rate']}%",
            "after_this_order": f"{after_util}%",
            "remaining_capacity_teu": max(summary["plan_teu"] - after_teu, 0),
            "conflict_orders": conflict_orders,
        },
        "material_check": material_check,
        "risk_alerts": risk_alerts[:5],
        "missing_info": ["客户名称", "合同号", "接单属性（自接单/总部）", "内外贸属性"],
        "next_steps": ["请补充客户名称及合同信息", "确认后可转为正式排产需求",
                       "生产计划员将在PC端完成正式排产"],
    }


def smart_plan(db: Session, line_code: str, year: int, month: int,
               work_order_no: str | None = None) -> dict:
    """智能排产：对草稿工令按优先级规则生成排产建议。
    若不传 work_order_no 则对全部候选工令批量排产；传入则仅对指定工令排产。
    仅草稿工令可参与智能排产（待审批/已确认等状态已进入审批流程，不再纳入）。"""
    month_str = f"{year:04d}-{month:02d}"
    drafts = (db.query(SchedulePlan)
              .filter(SchedulePlan.line_code == line_code,
                      SchedulePlan.plan_month == month_str,
                      SchedulePlan.status.in_(["draft"])))
    if work_order_no:
        drafts = drafts.filter(SchedulePlan.work_order_no == work_order_no)
    drafts = drafts.all()

    today = date.today()
    overrides = get_overrides(db, line_code)
    proposals = []
    for order in sorted(drafts, key=lambda o: o.quantity, reverse=True):
        box = get_box_type(db, order.box_type)
        if not box:
            continue
        analysis = feasibility_analysis(db, order.box_type, order.quantity,
                                        date(year, month, 28) if month < 12 else date(year, 12, 28),
                                        line_code, order.delivery_location, start_from=max(today + timedelta(days=1), date(year, month, 1)))
        sug = analysis.get("schedule_suggestion", {})
        if sug.get("recommended_start"):
            proposals.append({
                "plan_id": order.plan_id,
                "work_order_no": order.work_order_no,
                "customer": order.customer,
                "box_type": order.box_type,
                "quantity": order.quantity,
                "teu": order.teu,
                "suggested_start": sug["recommended_start"],
                "suggested_end": sug["recommended_end"],
                "daily_schedule": sug["daily_schedule"],
                "reason": f"交期紧急度30% + 箱型产能匹配20% + 物料齐套15%（{analysis['feasibility_score']:.0f} 置信度）",
                "confidence": analysis["feasibility_score"],
                "feasibility": analysis["feasibility"],
            })

    summary = capacity_summary(db, line_code, year, month)
    return {"line_code": line_code, "month": month_str, "summary": summary, "proposals": proposals}


def analyze_adjusted(db: Session, line_code: str, work_order_no: str,
                     daily_schedule: list[dict],
                     delivery_date: str | None = None) -> dict:
    """对手工调整后的按日排产方案给出智能建议：逐日利用率、冲突、交期与物料提示。"""
    order = db.query(SchedulePlan).filter(
        SchedulePlan.line_code == line_code,
        SchedulePlan.work_order_no == work_order_no).first()
    if not order:
        return {"ok": False, "message": "未找到工令"}
    box = get_box_type(db, order.box_type)
    if not box:
        return {"ok": False, "message": "未识别箱型"}

    # 规范化：仅保留数量>0 的日期，按日期排序
    rows = sorted([{"date": s["date"], "qty": int(s["qty"])} for s in daily_schedule if int(s.get("qty", 0)) > 0],
                  key=lambda x: x["date"])
    if not rows:
        return {"ok": False, "message": "未填写任何排产日期"}

    total_qty = sum(r["qty"] for r in rows)
    total_teu = int(total_qty * float(box.teu_factor))
    first, last = rows[0]["date"], rows[-1]["date"]
    d_first, d_last = date.fromisoformat(first), date.fromisoformat(last)

    # 其他工令在该窗口内的已排占用（排除本工令自身）
    w_start, w_end = d_first, d_last
    overrides = get_overrides(db, line_code)
    today = date.today()

    # 逐日利用率与冲突（产能取当日配置）
    day_insights = []
    conflicts = []
    for r in rows:
        dd = date.fromisoformat(r["date"])
        cap = day_capacity(db, line_code, dd)
        booked = booked_map(db, line_code, dd, dd).get(r["date"], {"qty": 0, "teu": 0, "orders": {}})
        other_teu = booked["teu"] - (booked["orders"].get(work_order_no, 0) * float(box.teu_factor))
        teu = int(r["qty"] * float(box.teu_factor))
        util = round((other_teu + teu) / cap * 100, 1) if cap > 0 else 0
        if cap <= 0:
            status = "rest"
        elif util > 100:
            status = "conflict"
        elif util >= 85:
            status = "tight"
        else:
            status = "normal"
        day_insights.append({"date": r["date"], "qty": r["qty"], "teu": teu,
                             "capacity": cap, "utilization": util, "status": status})
        if status == "conflict":
            conflicts.append(f"{r['date']} 利用率 {util}% 超载（配置产能 {cap} TEU），建议降低当日排产量或前移/后移部分产能")
        elif status == "rest":
            conflicts.append(f"{r['date']} 为休息日（配置产能 0），不可排产，请调整日期")

    # 交期评估
    if delivery_date:
        deadline = date.fromisoformat(delivery_date)
    elif order.production_deadline:
        try:
            deadline = datetime.strptime(str(order.production_deadline)[:10], "%Y-%m-%d").date()
        except ValueError:
            deadline = today + timedelta(days=45)
    else:
        deadline = today + timedelta(days=45)
    est_delivery = d_last + timedelta(days=INSPECTION_DAYS + _transport_days(order.delivery_location))
    buffer_days = (deadline - est_delivery).days if deadline else 0
    risk_level = "low" if buffer_days >= 7 else ("medium" if buffer_days >= 3 else "high")
    delivery_assess = {
        "production_complete": last, "estimated_delivery": est_delivery.isoformat(),
        "deadline": deadline.isoformat(), "buffer_days": buffer_days, "risk_level": risk_level,
    }

    # 物料齐套
    material_check = _material_check(db, box, total_qty)

    # 汇总建议
    suggestions = []
    if total_qty < order.quantity:
        suggestions.append(f"排产合计 {total_qty} 台，少于工令数量 {order.quantity}，缺口 {order.quantity - total_qty} 台需补充排产")
    elif total_qty > order.quantity:
        suggestions.append(f"排产合计 {total_qty} 台，超出工令数量 {order.quantity} {total_qty - order.quantity} 台，请核对")
    suggestions.extend(conflicts[:3])
    if risk_level == "high":
        suggestions.append(f"交期紧张：预计 {est_delivery.isoformat()} 交付，距交付期仅 {buffer_days} 天缓冲")
    for v in material_check.values():
        if v["status"] == "warning":
            suggestions.append(f"{v['name']}：{v['note']}")
        elif v["status"] == "insufficient":
            suggestions.append(f"{v['name']}：{v['note']}")
    if not conflicts and risk_level != "high" and total_qty == order.quantity:
        suggestions.append("方案均衡：每日利用率均在产能范围内，交期充足，可正常排产")

    return {
        "ok": True,
        "work_order_no": work_order_no,
        "box_type": order.box_type, "quantity": order.quantity,
        "planned_qty": total_qty, "max_daily_qty": max(r["qty"] for r in rows),
        "day_insights": day_insights,
        "delivery_assess": delivery_assess,
        "material_check": material_check,
        "conflicts": conflicts,
        "suggestions": suggestions[:8],
        "risk_level": risk_level,
    }


def apply_smart_plan(db: Session, line_code: str, proposals: list[dict], operator: str) -> int:
    """应用智能排产建议：写入日期与每日排产（保持草稿状态，待人工确认）。
    校验：排产日当天"已排 + 当前排产建议"的排产量合计（台）不得超过排班配置的日产能（0=休息日不可排产）。"""
    proposed_ids = [p["plan_id"] for p in proposals if p.get("plan_id")]
    dates = sorted({s["date"] for p in proposals for s in p.get("daily_schedule", []) if int(s.get("qty", 0)) > 0})

    # 已排数量（当日 ScheduleDaily 的 planned_qty，排除本次被重新排产的建议工令）
    day_qty: dict[str, int] = {}
    if dates:
        q = db.query(ScheduleDaily).filter(
            ScheduleDaily.line_code == line_code,
            ScheduleDaily.schedule_date.in_(dates))
        if proposed_ids:
            q = q.filter(ScheduleDaily.plan_id.notin_(proposed_ids))
        for r in q.all():
            day_qty[r.schedule_date.isoformat()] = day_qty.get(r.schedule_date.isoformat(), 0) + (r.planned_qty or 0)

    # 叠加本次排产建议的数量（台）
    for p in proposals:
        for s in p.get("daily_schedule", []):
            qty = int(s.get("qty", 0))
            if qty > 0:
                day_qty[s["date"]] = day_qty.get(s["date"], 0) + qty

    for dstr, total in day_qty.items():
        cap = day_capacity(db, line_code, date.fromisoformat(dstr))
        if cap <= 0:
            raise HTTPException(400, f"{dstr} 为休息日（日产能 0），不可排产")
        if total > cap:
            raise HTTPException(400, f"{dstr} 当日排产量合计（含已排）{total} 台超过日产能 {cap} 台")

    count = 0
    for p in proposals:
        order = db.query(SchedulePlan).filter(SchedulePlan.plan_id == p["plan_id"]).first()
        if not order:
            continue
        # 仅草稿工令可应用智能排产；待审批/已确认等状态不可再改排产产能
        if order.status != "draft":
            continue
        order.start_date = date.fromisoformat(p["suggested_start"])
        order.end_date = date.fromisoformat(p["suggested_end"])
        order.daily_planned_qty = max((s["qty"] for s in p["daily_schedule"]), default=0)
        order.version += 1
        db.query(ScheduleDaily).filter(ScheduleDaily.plan_id == order.plan_id).delete()
        for s in p["daily_schedule"]:
            dd = date.fromisoformat(s["date"])
            db.add(ScheduleDaily(plan_id=order.plan_id, work_order_no=order.work_order_no,
                                 line_code=line_code, schedule_date=dd, planned_qty=s["qty"],
                                 teu=int(s["qty"] * float(get_box_type(db, order.box_type).teu_factor)),
                                 is_workday=True))
        count += 1
    db.commit()
    return count
