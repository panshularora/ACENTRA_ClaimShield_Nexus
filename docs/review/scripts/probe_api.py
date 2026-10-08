"""Probe the running ClaimShield API: logins, queue, case packs, RBAC."""
import json, sys
import httpx

BASE = "http://127.0.0.1:8000"
USERS = {
    "manager": ("manager@demo.claimshield", "demo-manager"),
    "investigator": ("investigator@demo.claimshield", "demo-investigator"),
    "investigator2": ("investigator2@demo.claimshield", "demo-investigator2"),
    "analyst": ("analyst@demo.claimshield", "demo-analyst"),
    "auditor": ("auditor@demo.claimshield", "demo-auditor"),
    "admin": ("admin@demo.claimshield", "demo-admin"),
}
out = {}
clients = {}
for role, (email, pw) in USERS.items():
    c = httpx.Client(base_url=BASE, timeout=60)
    r = c.post("/api/v1/auth/login", json={"email": email, "password": pw})
    out[f"login_{role}"] = r.status_code
    clients[role] = c
run = clients["manager"].get("/api/v1/runs/current").json()
run_id = run["run_id"]
queue = clients["manager"].get(f"/api/v1/runs/{run_id}/queue").json()
out["queue_len"] = len(queue)
out["queue"] = [
    {k: q[k] for k in ("case_id", "lane", "primary_entity_id", "entity_ids", "harm", "flagged_dollars",
                       "evidence_strength", "p_confirm", "f30", "f60", "f90", "queue_rank")}
    for q in queue
]
json.dump(out, sys.stdout, indent=1)
# RBAC matrix on a sample case
cid = queue[0]["case_id"]
paths = ["/api/v1/runs/current", f"/api/v1/runs/{run_id}/queue", f"/api/v1/cases/{cid}",
         f"/api/v1/cases/{cid}/brief", f"/api/v1/cases/{cid}/claims", f"/api/v1/cases/{cid}/claims?unmask=true",
         f"/api/v1/cases/{cid}/network", "/api/v1/audit", "/api/v1/wiki/proposals", "/api/v1/batches"]
print("\nRBAC GET matrix (case", cid, ")")
print("path".ljust(60), *[r[:6].ljust(7) for r in USERS])
for p in paths:
    print(p.replace(cid, "{cid}").replace(run_id, "{run}").ljust(60),
          *[str(clients[r].get(p).status_code).ljust(7) for r in USERS])
