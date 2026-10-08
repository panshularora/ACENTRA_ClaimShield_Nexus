"""Security / correctness probes against the running API (writes a few demo decisions)."""
import httpx, json
B = "http://127.0.0.1:8000"
def login(email, pw):
    c = httpx.Client(base_url=B, timeout=60)
    r = c.post("/api/v1/auth/login", json={"email": email, "password": pw}); r.raise_for_status()
    return c
inv = login("investigator@demo.claimshield", "demo-investigator")
inv2 = login("investigator2@demo.claimshield", "demo-investigator2")
mgr = login("manager@demo.claimshield", "demo-manager")
aud = login("auditor@demo.claimshield", "demo-auditor")
run = inv.get("/api/v1/runs/current").json()
q = inv.get(f"/api/v1/runs/{run['run_id']}/queue").json()
overflow = [x["case_id"] for x in q if x["lane"] == "overflow"]
def show(name, r):
    try: body = r.json()
    except Exception: body = r.text[:200]
    if isinstance(body, dict): body = {k: body[k] for k in list(body)[:6]}
    print(f"{name}: {r.status_code} {json.dumps(body, default=str)[:260]}")
print("meta (unauthenticated):", httpx.get(B + "/api/v1/meta").json().get("demo_users", [])[:2])
# 1 CSRF: POST without X-CSRF-Token header
show("assign w/o CSRF header", inv.post(f"/api/v1/cases/{overflow[0]}/assign", json={}))
# 2 auditor unmask
r = aud.get(f"/api/v1/cases/{overflow[0]}/claims?unmask=true").json()
print("auditor unmask=true masked flag:", r["masked"], "first member:", r["rows"][0]["member"] if r["rows"] else None)
r = inv.get(f"/api/v1/cases/{overflow[0]}/claims?unmask=true").json()
print("investigator unmask=true masked flag:", r["masked"], "first member:", r["rows"][0]["member"] if r["rows"] else None)
r = inv.get(f"/api/v1/cases/{overflow[0]}/claims").json()
print("investigator masked row member payload:", r["rows"][0]["member"] if r["rows"] else None)
# 3 decision by non-assignee investigator2 on case assigned to investigator
show("inv2 decides case owned by inv", inv2.post(f"/api/v1/cases/{overflow[0]}/decisions", json={"action": "monitor", "reason": "Probe: non-assignee recording a decision on this case."}))
# 4 repeat decision on already-decided case
show("inv decides same case again (escalate)", inv.post(f"/api/v1/cases/{overflow[0]}/decisions", json={"action": "escalate", "reason": "Probe: second decision on an already decided case."}))
show("inv decides closed (escalated) case again (dismiss)", inv.post(f"/api/v1/cases/{overflow[0]}/decisions", json={"action": "dismiss", "reason": "Probe: third decision after escalation, should be blocked."}))
# 5 validation
show("bad action", inv.post(f"/api/v1/cases/{overflow[1]}/decisions", json={"action": "fraud", "reason": "x" * 25}))
show("short reason", inv.post(f"/api/v1/cases/{overflow[1]}/decisions", json={"action": "monitor", "reason": "short"}))
show("unknown case", inv.get("/api/v1/cases/CASE-NOPE"))
show("evidence provider outside case", inv.get(f"/api/v1/cases/{overflow[1]}/evidence/provider:{q[0]['primary_entity_id']}"))
show("hops=3", inv.get(f"/api/v1/cases/{overflow[1]}/network?hops=3"))
show("huge reason (200k chars)", inv.post(f"/api/v1/cases/{overflow[2]}/decisions", json={"action": "monitor", "reason": "A" * 200000}))
# 6 manager self-approves own precedent
d = mgr.post(f"/api/v1/cases/{overflow[3]}/decisions", json={"action": "escalate", "reason": "Manager escalates and then approves own precedent (probe)."}).json()
pid = d["proposal"]["proposal_id"]
show("manager approves own proposal", mgr.post(f"/api/v1/wiki/proposals/{pid}:approve", json={"note": "self"}))
show("approve twice", mgr.post(f"/api/v1/wiki/proposals/{pid}:approve", json={"note": "again"}))
# 7 refresh reuse detection persists?
c = httpx.Client(base_url=B, timeout=60)
c.post("/api/v1/auth/login", json={"email": "analyst@demo.claimshield", "password": "demo-analyst"})
old = c.cookies.get("cs_refresh")
r1 = c.post("/api/v1/auth/refresh"); print("refresh1", r1.status_code)
r2 = httpx.post(B + "/api/v1/auth/refresh", cookies={"cs_refresh": old}); print("replay old refresh", r2.status_code, r2.json().get("detail"))
r3 = c.post("/api/v1/auth/refresh"); print("legit refresh after reuse (should be 401 if revocation persisted):", r3.status_code, r3.json().get("detail"))
# 8 rate limit
bad = httpx.Client(base_url=B)
codes = [bad.post("/api/v1/auth/login", json={"email": "admin@demo.claimshield", "password": "wrongpass"}).status_code for _ in range(7)]
print("7 bad logins:", codes)
# 9 audit
a = httpx.Client(base_url=B, timeout=60); a.post("/api/v1/auth/login", json={"email": "auditor@demo.claimshield", "password": "demo-auditor"})
log = a.get("/api/v1/audit").json()
from collections import Counter
print("audit verification:", log["verification"], Counter(e["action"] for e in log["events"]))
