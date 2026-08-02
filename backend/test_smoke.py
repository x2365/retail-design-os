"""Smoke/integration tests — самодостаточны (не зависят от демо-изделий).

Сид теперь создаёт только справочники (пользователи, группы, бренды, ТТ);
изделия заполняются вручную. Поэтому тест сам создаёт задачу и проверяет поток.
"""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_smoke.db"
os.environ["JWT_SECRET"] = "test-secret"
os.environ.setdefault("UPLOAD_DIR", "./test_smoke_uploads")
if os.path.exists("test_smoke.db"):
    os.remove("test_smoke.db")

import re  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402

fails = []
def check(name, cond, extra=""):
    if not cond: fails.append(name)
    print(f"[{'OK ' if cond else 'FAIL'}] {name} {extra}")

c = TestClient(app).__enter__()
def login(email, pw):
    return c.post("/api/auth/login", data={"username": email, "password": pw})

# --- auth ---
r = login("admin@retail.os", "admin123")
check("admin login 200", r.status_code == 200, r.text[:80])
admin = {"Authorization": f"Bearer {r.json()['access_token']}"}
check("login returns user role", r.json()["user"]["role"] == "admin")
check("bad password 401", login("admin@retail.os", "nope").status_code == 401)
check("no-token kpis 401", c.get("/api/dashboard/kpis").status_code == 401)
check("me", c.get("/api/auth/me", headers=admin).json()["email"] == "admin@retail.os")

# --- reference data kept; products empty ---
k = c.get("/api/dashboard/kpis", headers=admin).json()
check("kpi brands=13", k["brands_count"] == 13, k.get("brands_count"))
check("kpi active=0 (no products)", k["active_tasks"] == 0, k.get("active_tasks"))
d = c.get("/api/tasks", headers=admin, params={"page_size": 200}).json()
check("tasks empty", d["total"] == 0, d["total"])
rp = c.get("/api/retail-points", headers=admin, params={"page_size": 5}).json()
check("retail points total=90", rp["total"] == 90, rp["total"])
names = " ".join(p["name"] for p in rp["items"])
check("stores renamed → Золотое Яблоко", "Золотое Яблоко" in names and "Иль" not in names, names[:60])
check("approvals empty", len(c.get("/api/approvals", headers=admin).json()) == 0)
check("payments empty", len(c.get("/api/payments", headers=admin).json()) == 0)

# --- RBAC + create ---
viewer = {"Authorization": f"Bearer {login('viewer@retail.os','viewer123').json()['access_token']}"}
check("viewer create -> 403",
      c.post("/api/tasks", headers=viewer, json={"name": "X", "brand": "Darling"}).status_code == 403)
mgr = {"Authorization": f"Bearer {login('manager@retail.os','manager123').json()['access_token']}"}
r = c.post("/api/tasks", headers=mgr, json={"name": "Тестовый дисплей", "brand": "Darling", "tt_total": 0})
check("manager create -> 201", r.status_code == 201, r.text[:80])
code = r.json()["code"]
check("code looks like RD-NNN", bool(re.match(r"^RD-\d{3}$", code)), code)

# --- stage transitions: +1 ok, skip 422 ---
check("patch +1 -> 200", c.patch(f"/api/tasks/{code}", headers=mgr, json={"stage": 2}).json()["stage"] == 2)
check("skip-forward -> 422", c.patch(f"/api/tasks/{code}", headers=mgr, json={"stage": 5}).status_code == 422)

# --- shipment docs stage fields + new doc kinds ---
r = c.patch(f"/api/tasks/{code}", headers=mgr,
            json={"shipment_order_no": "ORD-1", "shipment_ship_date": "2026-07-01"})
check("shipment order saved", r.json()["shipment_order_no"] == "ORD-1", r.json().get("shipment_order_no"))
r = c.post(f"/api/tasks/{code}/documents", headers=mgr, data={"kind": "waybill", "stage": "2"},
           files={"file": ("n.pdf", b"%PDF", "application/pdf")})
check("waybill upload -> Накладная", r.status_code == 201 and r.json()["kind_label"] == "Накладная", r.text[:80])

# --- CLOSED gating: advance to 11 (satisfying each stage gate), close blocked (no payment) ---
gcode = c.post("/api/tasks", headers=mgr, json={"name": "gate", "brand": "Darling", "tt_total": 0,
                                                "brief_data": {"product_name": "gate"}}).json()["code"]
c.patch(f"/api/tasks/{gcode}", headers=mgr, json={"stage": 2})                       # 1->2 (ТЗ заполнено)
c.post(f"/api/tasks/{gcode}/documents", headers=mgr, data={"kind": "sketch", "stage": "2"},
       files={"file": ("d.png", b"x", "image/png")})
c.patch(f"/api/tasks/{gcode}", headers=mgr, json={"stage": 3})                       # 2->3 (есть дизайн)
c.post(f"/api/tasks/{gcode}/prep-approval", headers=mgr, json={"gate": "brand", "approved": True})
c.post(f"/api/tasks/{gcode}/prep-approval", headers=mgr, json={"gate": "zya", "approved": True})  # 3->4 авто
c.patch(f"/api/tasks/{gcode}", headers=mgr, json={"stage": 5})                       # 4->5
c.post(f"/api/tasks/{gcode}/kp-approval", headers=mgr, json={"gate": "manager", "approved": True})
c.post(f"/api/tasks/{gcode}/kp-approval", headers=mgr, json={"gate": "director", "approved": True})
c.post(f"/api/tasks/{gcode}/kp-approval", headers=mgr, json={"gate": "network", "approved": True})  # 5->6 авто
c.post(f"/api/tasks/{gcode}/documents", headers=mgr, data={"kind": "ds", "stage": "6"},
       files={"file": ("ds.pdf", b"%PDF", "application/pdf")})
c.post(f"/api/tasks/{gcode}/documents", headers=mgr, data={"kind": "invoice", "stage": "6"},
       files={"file": ("inv.pdf", b"%PDF", "application/pdf")})
c.patch(f"/api/tasks/{gcode}", headers=mgr, json={"stage": 7})                       # 6->7 (ДС+счёт)
c.post(f"/api/tasks/{gcode}/sample-approval", headers=mgr, json={"approved": True})
for s in range(8, 12):
    c.patch(f"/api/tasks/{gcode}", headers=mgr, json={"stage": s})                   # 7->8...10->11
rclose = c.patch(f"/api/tasks/{gcode}", headers=mgr, json={"stage": 12})
check("close gated -> 422", rclose.status_code == 422, rclose.status_code)
check("gated stays 11", c.get(f"/api/tasks/{gcode}", headers=mgr).json()["stage"] == 11)
# stage-approval on current stage surfaces blocked_reasons (no advance)
rr = c.patch(f"/api/tasks/{gcode}/stage-approval", headers=mgr, json={"stage": 11, "approved": True}).json()
check("blocked_reasons surfaced", rr["stage"] == 11 and len(rr.get("blocked_reasons", [])) > 0, rr.get("blocked_reasons"))

print("\n" + ("ALL PASSED" if not fails else f"FAILURES: {fails}"))
sys.exit(1 if fails else 0)
