"""后端冒烟测试：直接调用 TestClient 验证各核心接口"""
import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

# 重置数据库，保证测试可重复运行（种子数据在 startup 重新写入）
_db_file = Path(__file__).parent / "data" / "containermind.db"
if _db_file.exists():
    _db_file.unlink()

from app.main import app

client = TestClient(app)
client.__enter__()  # 触发 startup：建表 + 种子数据


def check(name, resp, keys=None):
    ok = resp.status_code == 200
    print(f"[{'OK' if ok else 'FAIL'}] {name} -> {resp.status_code}")
    if not ok:
        print(resp.text[:500])
        return False
    if keys:
        data = resp.json()
        for k in keys:
            if isinstance(k, str) and k not in data:
                print(f"  missing key: {k}; got: {list(data)[:10]}")
                return False
    return True


results = []
results.append(check("health", client.get("/api/v1/health")))
results.append(check("factories", client.get("/api/v1/meta/factories")))
results.append(check("box-types", client.get("/api/v1/meta/box-types")))
results.append(check("materials", client.get("/api/v1/meta/materials")))
results.append(check("login", client.post("/api/v1/auth/login", json={"username": "zhang", "password": "123456"})))
results.append(check("dashboard", client.get("/api/v1/dashboard/overview"), ["kpi", "line_status", "capacity_chart"]))
results.append(check("schedule", client.get("/api/v1/planning/schedule?line_code=PD-D&month=2026-08"), ["summary", "orders", "calendar"]))
results.append(check("calendar", client.get("/api/v1/planning/calendar?line_code=PD-D&month=2026-08")))
results.append(check("gantt", client.get("/api/v1/planning/gantt-data?line_code=PD-D&month=2026-08")))
results.append(check("gantt-days", client.get("/api/v1/planning/gantt-days?line_code=PD-D&month=2026-08"), ["days", "orders", "daily_total"]))
results.append(check("conflicts", client.get("/api/v1/planning/conflicts?line_code=PD-D&month=2026-08")))
results.append(check("capacity", client.get("/api/v1/planning/capacity-summary?line_code=PD-D&month=2026-08"), ["plan_teu", "scheduled_teu"]))
results.append(check("approval-list", client.get("/api/v1/approval/list?status=pending"), ["counts", "items"]))
results.append(check("agents-diag", client.get("/api/v1/agents/diagnosis?device_id=WLD-R03")))
results.append(check("agents-supply", client.get("/api/v1/agents/supply-chain")))
results.append(check("agents-cost", client.get("/api/v1/agents/cost-analysis")))

# 智能排产
r = client.post("/api/v1/planning/smart", json={"line_code": "PD-D", "month": "2026-08", "apply": False})
results.append(check("smart-plan", r, ["proposals", "summary"]))
r = client.post("/api/v1/planning/smart", json={"line_code": "PD-D", "month": "2026-08", "apply": False, "work_order_no": "SHPD-2026-281-DS"})
results.append(check("smart-single", r, ["proposals", "summary"]))
r = client.post("/api/v1/planning/smart/adjust-analyze", json={"line_code": "PD-D", "work_order_no": "SHPD-2026-281-DS", "daily_schedule": [{"date": "2026-08-18", "qty": 40}, {"date": "2026-08-19", "qty": 40}]})
results.append(check("smart-adjust-analyze", r, ["suggestions", "delivery_assess"]))

# what-if（核心场景：40HC 1000台 9/30 上海）
r = client.post("/api/v1/planning/what-if", json={
    "box_type": "40HC", "quantity": 1000, "delivery_date": "2026-09-30", "delivery_location": "上海"})
results.append(check("what-if", r))
data = r.json()
print("  what-if feasibility:", data.get("feasibility"),
      "| window:", data.get("schedule_suggestion", {}).get("recommended_start"),
      "~", data.get("schedule_suggestion", {}).get("recommended_end"),
      "| days:", len(data.get("schedule_suggestion", {}).get("daily_schedule", [])))

# 移动端快速录单
r = client.post("/api/v1/mobile/quick-order", json={"text": "意向新订单，40HC箱型，总数量1000，计划2026.09.30交付，交付地点上海"})
results.append(check("quick-order", r))
data = r.json()
print("  intent:", data.get("intent"), "| box:", data.get("order_info", {}).get("box_type"),
      "| qty:", data.get("order_info", {}).get("quantity"))
if data.get("schedule_analysis"):
    print("  feasibility:", data["schedule_analysis"].get("feasibility"))

# 口语化解析
r = client.post("/api/v1/mobile/quick-order", json={"text": "客户要200台20GP，10月底要，能排上吗"})
data = r.json()
print("  colloquial intent:", data.get("intent"), "| box:", data.get("order_info", {}).get("box_type"),
      "| qty:", data.get("order_info", {}).get("quantity"), "| teu:", data.get("order_info", {}).get("teu"))

# 确认录入
r = client.post("/api/v1/mobile/quick-order/confirm", json={
    "box_type": "40HC", "quantity": 1000, "delivery_date": "2026-09-30",
    "delivery_location": "上海", "customer": "中远海运", "teu": 2000, "input_text": "测试"})
results.append(check("quick-order-confirm", r))

results.append(check("my-orders", client.get("/api/v1/mobile/my-orders?user=张业务")))
results.append(check("capacity-brief", client.get("/api/v1/mobile/capacity-brief?line_code=PD-D&month=2026-08")))
results.append(check("notifications", client.get("/api/v1/mobile/notifications?user=张业务")))
results.append(check("mobile-approvals", client.get("/api/v1/mobile/approvals?status=pending")))

# orchestrator chat（非流式）
r = client.post("/api/v1/orchestrator/chat", json={"message": "9月份PD-D线还有多少空位", "source": "pc"})
results.append(check("chat-capacity", r))
print("  reply:", r.json().get("reply_text", "")[:80])

r = client.post("/api/v1/orchestrator/chat", json={"message": "SHPD-2026-281-DS排到几号了", "source": "pc"})
results.append(check("chat-schedule", r))
print("  reply:", r.json().get("reply_text", "")[:80])

# SSE 流式
with client.stream("POST", "/api/v1/orchestrator/chat/stream",
                   json={"message": "意向新订单，40HC箱型，总数量1000，计划2026.09.30交付，交付地点上海"}) as resp:
    events = []
    for line in resp.iter_lines():
        if line.startswith("event:"):
            events.append(line.split(":", 1)[1].strip())
    print("[OK] chat-stream events:", events[:10])
    results.append("result" in events and "done" in events)

# 审批操作
r = client.post("/api/v1/approval/1/approve", json={"operator": "张主管", "comment": "同意"})
results.append(check("approve", r))

# 创建工令
r = client.post("/api/v1/planning/manual", json={
    "work_order_no": "", "customer": "测试客户", "box_type": "20GP", "quantity": 60,
    "start_date": "2026-08-17", "end_date": "2026-08-18"})
results.append(check("create-order", r))
if r.status_code == 200:
    pid = r.json()["plan"]["id"]
    r2 = client.post(f"/api/v1/planning/schedule/{pid}/confirm?operator=李计划")
    results.append(check("confirm-order", r2))
    r3 = client.delete(f"/api/v1/planning/schedule/{pid}")
    results.append(check("delete-order", r3))

print("\n=== PASSED:", sum(1 for x in results if x), "/", len(results), "===")
sys.exit(0 if all(results) else 1)
