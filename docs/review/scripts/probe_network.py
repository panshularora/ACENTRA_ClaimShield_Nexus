"""Dump network/claims/brief/timeline packs for every case and summarise graph linkage."""
import collections, json, sys
import httpx
c = httpx.Client(base_url="http://127.0.0.1:8000", timeout=60)
c.post("/api/v1/auth/login", json={"email": "investigator@demo.claimshield", "password": "demo-investigator"})
run = c.get("/api/v1/runs/current").json()
queue = c.get(f"/api/v1/runs/{run['run_id']}/queue").json()
dump = {}
for q in queue:
    cid = q["case_id"]
    case = c.get(f"/api/v1/cases/{cid}").json()
    net = c.get(f"/api/v1/cases/{cid}/network").json()
    claims = c.get(f"/api/v1/cases/{cid}/claims").json()
    tl = c.get(f"/api/v1/cases/{cid}/timeline").json()
    brief = c.get(f"/api/v1/cases/{cid}/brief").json()
    dump[cid] = {"case": case, "network": net, "claims": claims, "timeline": tl, "brief": brief}
    types = collections.Counter(n["type"] for n in net["nodes"])
    kinds = collections.Counter(e["kind"] for e in net["edges"])
    ids = {n["id"] for n in net["nodes"]}
    deg = collections.Counter()
    for e in net["edges"]:
        deg[e["source"]] += 1; deg[e["target"]] += 1
    isolated = [n["id"] for n in net["nodes"] if deg[n["id"]] == 0]
    alert_entities = {a["entity_id"] for a in case["alerts"]}
    case_entities = set(case["entity_ids"])
    missing_case_npis = sorted(case_entities - ids)
    ring_kinds = sorted({k for a in case["alerts"] for k in (a["evidence"].get("edge_kinds") or [])})
    node_keys = sorted({k for n in net["nodes"] for k in n})
    print(f"{cid} lane={q['lane']:<14} npis={len(case_entities)} alerts={len(case['alerts'])} "
          f"nodes={len(net['nodes'])} {dict(types)} edges={len(net['edges'])} {dict(kinds)} "
          f"isolated={len(isolated)} case_npis_missing_from_graph={missing_case_npis} "
          f"alert_edge_kinds={ring_kinds} node_fields={node_keys}")
json.dump(dump, open("/workspace/claimshield-review/logs/case_packs.json", "w"), indent=1, default=str)
