"""Quick scheme-level recall/precision of the current detectors on tiny seed 7 (not in repo; M14 is missing)."""
import ast
from claimshield.synth.generator import generate
from claimshield.pipeline.service import detect
ds = generate("tiny", 7)
res = detect(ds.tables, horizon_days=60, recovery=0.5, harm_lambda=250.0, capacity_hours=40.0)
gt = ds.ground_truth
flag_providers = {e for c in res["cases"] for e in c["entity_ids"]}
flag_lines = {l for a in res["alerts"] for l in a.line_ids}
today = {e for c in res["cases"] if c["lane"] in ("harm_priority", "selected") for e in c["entity_ids"]}
rows = []
fraud_prov = set()
for _, r in gt.iterrows():
    ents = {str(x) for x in (ast.literal_eval(r.entity_ids) if isinstance(r.entity_ids, str) else r.entity_ids or []) if str(x).startswith("PRV")}
    if isinstance(r.provider_id, str): ents.add(r.provider_id)
    lines = set(ast.literal_eval(r.line_ids)) if isinstance(r.line_ids, str) else set(r.line_ids or [])
    if r.is_fraud: fraud_prov |= ents
    hit_p = bool(ents & flag_providers); hit_l = len(lines & flag_lines) / len(lines) if lines else None
    rows.append((r.scheme_id, r.scheme_type, r.variant, bool(r.is_fraud), hit_p, None if hit_l is None else round(hit_l, 2), bool(ents & today)))
print("scheme  type                       var fraud provider_flagged line_recall on_today_desk")
for row in rows: print(f"{row[0]:<7} {row[1]:<26} {row[2]:<3} {str(row[3]):<5} {str(row[4]):<16} {str(row[5]):<11} {row[6]}")
fr = [r for r in rows if r[3]]; hn = [r for r in rows if not r[3]]
print(f"\nfraud schemes with >=1 provider flagged: {sum(r[4] for r in fr)}/{len(fr)}; hard negatives flagged: {sum(r[4] for r in hn)}/{len(hn)}")
print(f"flagged providers: {len(flag_providers)}; of which in a planted fraud scheme: {len(flag_providers & fraud_prov)}")
print(f"cases={len(res['cases'])} alerts={len(res['alerts'])}")
