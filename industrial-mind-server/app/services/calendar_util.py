"""排产日历工具：工作日/工时计算（默认周一至周五 8h，周末 0h，支持节假日覆盖）"""
from datetime import date, timedelta

# 2026 年节假日（演示数据，可按国务院放假安排调整）
HOLIDAYS_2026 = {
    # 元旦
    "2026-01-01", "2026-01-02", "2026-01-03",
    # 春节
    "2026-02-16", "2026-02-17", "2026-02-18", "2026-02-19", "2026-02-20",
    "2026-02-21", "2026-02-22",
    # 清明
    "2026-04-04", "2026-04-05", "2026-04-06",
    # 五一
    "2026-05-01", "2026-05-02", "2026-05-03", "2026-05-04", "2026-05-05",
    # 端午
    "2026-06-19", "2026-06-20", "2026-06-21",
    # 中秋
    "2026-09-25",
    # 国庆
    "2026-10-01", "2026-10-02", "2026-10-03", "2026-10-04",
    "2026-10-05", "2026-10-06", "2026-10-07",
}

WEEK_CN = ["一", "二", "三", "四", "五", "六", "日"]


def day_of_week_cn(d: date) -> str:
    return WEEK_CN[d.weekday()]


def default_workday(d: date) -> bool:
    return d.weekday() < 5 and d.isoformat() not in HOLIDAYS_2026


def month_days(year: int, month: int) -> list[date]:
    d = date(year, month, 1)
    days = []
    while d.month == month:
        days.append(d)
        d += timedelta(days=1)
    return days


def month_calendar(year: int, month: int, overrides: dict | None = None) -> list[dict]:
    """返回整月日历：[{date, is_workday, hours, day_of_week, note}]"""
    overrides = overrides or {}
    result = []
    for d in month_days(year, month):
        ov = overrides.get(d.isoformat())
        if ov:
            is_wd, hours, note = ov["is_workday"], ov["hours"], ov.get("note", "")
        else:
            is_wd, hours, note = default_workday(d), (8 if default_workday(d) else 0), ""
        result.append({
            "date": d.isoformat(),
            "day": d.day,
            "is_workday": is_wd,
            "hours": hours,
            "day_of_week": day_of_week_cn(d),
            "note": note,
        })
    return result


def workdays_between(start: date, end: date, overrides: dict | None = None) -> list[date]:
    overrides = overrides or {}
    out, d = [], start
    while d <= end:
        ov = overrides.get(d.isoformat())
        is_wd = ov["is_workday"] if ov else default_workday(d)
        if is_wd:
            out.append(d)
        d += timedelta(days=1)
    return out


def next_workdays(from_date: date, count: int, overrides: dict | None = None) -> list[date]:
    """自 from_date（含）起向后取 count 个工作日"""
    overrides = overrides or {}
    out, d = [], from_date
    while len(out) < count:
        ov = overrides.get(d.isoformat())
        is_wd = ov["is_workday"] if ov else default_workday(d)
        if is_wd:
            out.append(d)
        d += timedelta(days=1)
    return out
