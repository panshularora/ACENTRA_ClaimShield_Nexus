"""Load tiny seed 7 as manager and record one realistic investigator decision so the wiki loop has data."""
import json, httpx
B = "http://127.0.0.1:8000"
m = httpx.Client(base_url=B, timeout=120)
m.post("/api/v1/auth/login", json={"email": "manager@demo.claimshield", "password": "demo-manager"}).raise_for_status()
csrf = m.cookies.get("cs_csrf")
r = m.post("/api/v1/batches", json={"profile": "tiny", "seed": 7}, headers={"X-CSRF-Token": csrf}); r.raise_for_status()
run = r.json()["run"]; print("run", run["run_id"], run["n_alerts"], run["n_cases"], run["lanes"])
q = m.get(f"/api/v1/runs/{run['run_id']}/queue").json()
pick = {}
for c in q:
    if c["lane"] == "harm_priority" and len(c["entity_ids"]) >= 5 and "ring_harm" not in pick: pick["ring_harm"] = c["case_id"]
    if c["lane"] == "overflow" and len(c["entity_ids"]) >= 6 and "ring_backlog" not in pick: pick["ring_backlog"] = c["case_id"]
pick["top"] = q[0]["case_id"]
backlog_single = next(c["case_id"] for c in q if c["lane"] == "overflow" and len(c["entity_ids"]) == 1)
i = httpx.Client(base_url=B, timeout=60)
i.post("/api/v1/auth/login", json={"email": "investigator@demo.claimshield", "password": "demo-investigator"}).raise_for_status()
h = {"X-CSRF-Token": i.cookies.get("cs_csrf")}
i.post(f"/api/v1/cases/{backlog_single}/assign", json={}, headers=h).raise_for_status()
d = i.post(f"/api/v1/cases/{backlog_single}/decisions", headers=h, json={
    "action": "needs_evidence", "reason": "Duplicate pattern is plausible but the resubmission images are missing; request records.",
}); d.raise_for_status(); print("decision", d.json()["decision_id"], "proposal", d.json()["proposal"]["proposal_id"], "on", backlog_single)
pick["decided"] = backlog_single
json.dump(pick, open("/workspace/claimshield-review/logs/screen_cases.json", "w")); print(pick)
