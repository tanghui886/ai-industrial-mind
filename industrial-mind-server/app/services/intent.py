"""意图识别与信息抽取服务（规则引擎版，可被 LLM 增强）"""
import re
from datetime import date, timedelta

# 箱型匹配模式（按长度优先）
BOX_PATTERNS: list[tuple[str, str]] = [
    (r"40\s*['′]?\s*hcdd", "40HCDD"),
    (r"40\s*['′]?\s*hcfos", "40HCFOS"),
    (r"20\s*['′]?\s*duocon", "20DUOCON"),
    (r"20\s*['′]?\s*hcfos", "20HCFOS"),
    (r"45\s*['′]?\s*hc\s*气瓶箱|45气瓶箱", "45HC气瓶箱"),
    (r"40\s*['′]?\s*(?:gp)?\s*气瓶箱|40气瓶箱", "40气瓶箱"),
    (r"20\s*['′]?\s*(?:gp)?\s*气瓶箱|气瓶箱", "20气瓶箱"),
    (r"ener\s*d\s*max", "Ener D Max"),
    (r"ener\s*c\s*\+?", "Ener C+"),
    (r"ener\s*([ddefghswx])", "Ener_SERIES"),
    (r"30\s*ft?\s*滚装|30\s*['′]?\s*滚装|30ft车架", "30ft滚装车架"),
    (r"40\s*ft?\s*滚装|滚装车架|车架", "40ft滚装车架"),
    (r"40\s*['′]?\s*hc", "40HC"),
    (r"40\s*['′]?\s*gp", "40GP"),
    (r"20\s*['′]?\s*gp", "20GP"),
    (r"20\s*['′]?\s*os", "20OS"),
    (r"20\s*['′]?\s*hc储能", "20HC储能箱"),
    (r"储能箱", "20储能箱"),
    (r"液冷方舱|方舱", "液冷方舱"),
    (r"房屋箱", "房屋箱"),
    (r"光伏平板|光伏", "光伏平板"),
    (r"岸电箱", "岸电箱"),
]

LOCATIONS = ["上海", "青岛", "宁波", "天津", "深圳", "广州", "大连", "连云港",
             "南通", "启东", "南京", "厦门", "福州", "营口", "重庆", "武汉", "苏州", "杭州"]

LINES = [("pd-d", "PD-D"), ("特箱线", "PD-D"), ("浦东", "PD-D"),
         ("bs-a", "BS-A"), ("宝山", "BS-A"),
         ("js-a", "JS-A"), ("金山a", "JS-A"),
         ("js-b", "JS-B"), ("金山b", "JS-B"),
         ("fx-a", "FX-A"), ("奉贤", "FX-A")]

URGENT_WORDS = ["急", "加急", "紧急", "尽快", "马上"]

MONTH_END = re.compile(r"(\d{1,2})\s*月\s*(?:底|末|最后)")
FULL_DATE = re.compile(r"(20\d{2})\s*[年.\-/]\s*(\d{1,2})\s*[月.\-/]\s*(\d{1,2})")
MD_DATE = re.compile(r"(\d{1,2})\s*月\s*(\d{1,2})\s*[日号]?")
WORK_ORDER_NO = re.compile(r"[A-Za-z]{2,6}-\d{4}-\d{3,4}-[A-Za-z]{2,4}")


def _match_box_type(text: str) -> str | None:
    t = text.lower().replace("　", " ")
    for pat, code in BOX_PATTERNS:
        m = re.search(pat, t)
        if not m:
            continue
        if code == "Ener_SERIES":
            return f"Ener {m.group(1).upper()}"
        return code
    return None


def _match_quantity(text: str) -> int | None:
    for pat in [r"(?:总数量|数量|共计|一共|需要|要|采购|追加)\s*(\d{2,6})\s*(?:台|个|只)?",
                r"(\d{2,6})\s*(?:台|只)",
                r"(?:数量|要)\s*(\d{2,6})"]:
        m = re.search(pat, text)
        if m:
            return int(m.group(1))
    return None


def _match_date(text: str, today: date) -> date | None:
    m = FULL_DATE.search(text)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= mo <= 12 and 1 <= d <= 31:
            try:
                return date(y, mo, d)
            except ValueError:
                pass
    m = MONTH_END.search(text)
    if m:
        mo = int(m.group(1))
        if 1 <= mo <= 12:
            y = today.year if mo >= today.month else today.year + 1
            return _month_last_day(y, mo)
    m = MD_DATE.search(text)
    if m:
        mo, d = int(m.group(1)), int(m.group(2))
        y = today.year if mo >= today.month else today.year + 1
        try:
            return date(y, mo, d)
        except ValueError:
            pass
    if re.search(r"月(?:底|末)(?:前|之前)?交付?|月底要", text):
        mo = today.month + (1 if today.day > 20 else 0)
        y = today.year + (1 if mo > 12 else 0)
        mo = mo if mo <= 12 else 1
        return _month_last_day(y, mo)
    return None


def _month_last_day(y: int, m: int) -> date:
    if m == 12:
        return date(y, 12, 31)
    return date(y, m + 1, 1) - timedelta(days=1)


def _match_location(text: str) -> str | None:
    for loc in LOCATIONS:
        if loc in text:
            return loc
    return None


def _match_line(text: str) -> str | None:
    t = text.lower()
    for kw, code in LINES:
        if kw in t:
            return code
    # 通用产线编码识别：如 NH-A、PD-D、SH-A 等（即使不在已知产线表，也原样返回以便后续校验）
    m = re.search(r"(?:^|[^a-z0-9])([a-z]{1,3})\s*-\s*([a-z])(?=[^a-z0-9]|$)", t)
    if m and m.group(1) not in ("ft", "hc", "gp", "os") and "产线" in t:
        return f"{m.group(1).upper()}-{m.group(2).upper()}"
    return None


def _match_customer(text: str) -> str | None:
    m = re.search(r"客户(?:名称)?(?:是|为|:：)?\s*([\u4e00-\u9fa5A-Za-z0-9]{2,12})", text)
    return m.group(1) if m else None


def classify_intent(text: str) -> tuple[str, float]:
    t = text.lower()
    if re.search(r"意向|新订单|下单|接单|追加|要\d+台|需要\d+台|\d+台.*要|采购.*台|评估|能不能排|能排上", t):
        return "new_order_intent", 0.95
    m = WORK_ORDER_NO.search(text)
    if m or re.search(r"排到|排产.*(几号|什么时候|查询)|什么时候.*(生产|完工)|进度", t):
        return "schedule_query", 0.90
    if re.search(r"空位|产能|利用率|还能排|够不够|还有多少", t):
        return "capacity_query", 0.90
    if re.search(r"日产能|产能标准|产多少", t):
        return "capacity_query", 0.85
    if re.search(r"设备|设备情况|设备健康|设备异常|设备.*状况|产线.*设备|设备.*产线|诊断|机器人|健康状况|运维|点检|保养|报警", t):
        return "device_query", 0.90
    if re.search(r"物料|库存|缺料|断料|缺口|需补货|补货|在库|到货|采购|齐套", t):
        return "material_gap", 0.88
    if re.search(r"堆存|爆仓|剩余空间|预堆存|库容|堆存风险|堆放", t):
        return "storage_risk", 0.88
    if re.search(r"成本|成本动因|费用|单箱|毛利|利润|降本|花费", t):
        return "cost_analysis", 0.88
    return "general_chat", 0.6


def parse_intent(text: str, today: date | None = None) -> dict:
    """规则引擎意图识别 + 信息抽取，输出对齐方案 v6 的 JSON 结构"""
    today = today or date.today()
    intent, conf = classify_intent(text)
    box_type = _match_box_type(text)
    quantity = _match_quantity(text)
    delivery_date = _match_date(text, today)
    location = _match_location(text)
    customer = _match_customer(text)
    urgency = "high" if any(w in text for w in URGENT_WORDS) else None
    wo_match = WORK_ORDER_NO.search(text)

    extracted = {
        "box_type": box_type,
        "quantity": quantity,
        "delivery_date": delivery_date.isoformat() if delivery_date else None,
        "delivery_location": location,
        "customer": customer,
        "urgency": urgency,
        "line_code": _match_line(text),
        "work_order_no": wo_match.group(0) if wo_match else None,
        "what_if": bool(re.search(r"推迟|延后|改到|如果.*月", text)),
    }

    missing = []
    if intent == "new_order_intent":
        if not box_type:
            missing.append("箱型")
        if not quantity:
            missing.append("数量")
        if not delivery_date:
            missing.append("交付日期")
        if not customer:
            missing.append("客户名称")

    return {
        "intent": intent,
        "confidence": conf,
        "extracted_info": extracted,
        "missing_fields": missing,
        "clarification_needed": intent == "new_order_intent" and (not box_type or not quantity),
    }
