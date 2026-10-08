# API gaps found while building the UI

What the redesigned frontend needs from the API and does not get today. Each item says what the
UI does now and the shape it would use. Network items overlap with the backend work on
`fix/backend-p0`; the UI already reads those fields as optional (see
`src/components/network/graphModel.ts`) and will pick them up without a code change once the
names match. Field names below are proposals until `NETWORK_API.md` is published.

## Network (`GET /api/v1/cases/{id}/network`)

| Gap | UI today | Wanted shape |
|---|---|---|
| No `shared_contact` / `shared_owner` edges; the ring alerts' `edge_kinds` cite them, but the endpoint never reads `contact_point` | Shows TIN, address, owner and referral links only | `{ "source": "PRV-A", "target": "PRV-B", "kind": "shared_contact", "evidence_ids": ["contact:9f2c…"] }` |
| `shared_location` is a clique (28 edges for one address) | Merges duplicates; draws the clique | Address hub node `{ "id": "ADDR-…", "type": "address", "label": "12 Main St, …" }` plus `located_at` edges |
| Referral direction and volume are lost (edges deduplicated on a sorted key) | Draws referrals with the arrow in the order received, width 1 | `{ "kind": "referral", "source": "<referrer>", "target": "<receiver>", "direction": "out", "count": 37 }` |
| Nodes carry no case membership | Derives `inCase` from `case.entity_ids` and flagged claim lines | `"in_case": true, "is_subject": false` |
| Nodes carry no findings or dollars | Derives `alertIds` from `alerts[].entity_id` / `evidence.peer_ids` and flagged dollars/lines from `/claims` (case lines only) | `"alert_ids": ["ALR-…"], "flagged_paid": 12840.5, "n_flagged_lines": 31` |
| Edges carry no evidence reference | Edge card explains the kind only | `"evidence_ids": ["line:…", "own:…", "alert:…"]`, optional `"first_seen"`/`"last_seen"` |
| Neighbourhood is not capped (every referral of every provider; 19–33 providers per case) | Lists hops 1, 2 and "further out"; dims beyond the focus 2-hop | Cap at 2 hops from the subject (or top-k by volume), plus `"hop": 1` per node |
| Only the subject carries a risk value | Risk ring on the subject only (from case severity) | Optional per-node `"severity": 1–4` and `"harm": 0–4` for other case providers |
| No pagerank/community | Not shown | `"pagerank": 0.081, "community": 3` |
| No click-through for context nodes; `/claims` only returns the case's own lines | Selection card says "the API does not yet return claims for linked providers outside the case" | `GET /api/v1/entities/{id}/summary?case_id=…` → `{ "claims": {"n_lines": 120, "paid": 48210.0, "sample": [ClaimRow…]}, "alerts": [CaseAlert…], "cases": ["CASE-…"] }` |

## Brief and evidence

- No `node:` / `edge:` evidence kinds, so brief sentences cannot cite graph objects and the graph
  cannot highlight a cited link. Wanted: `{ "id": "edge:shared_tin:PRV-A--PRV-B", "kind": "edge", … }`
  in `/evidence/{id}` and in `cites[]`.
- Limitations and "recommended action" sentences cite `metric:harm` as boilerplate.

## Queue and capacity

- The harm reserve (`min(harm_hours, 35% · capacity)`) is not in the run payload, so the UI can
  only say the desk is over capacity, not by how much the reserve allowed. Wanted:
  `run.summary.harm_reserved_hours`, `run.summary.capacity_used_hours`.
- `ranking_policy.note` is free text; the UI repeats it. A structured list of steps would let the
  policy panel stay in sync with the backend.

## Decisions

- The decision set is changing (state escalation, manager-approved suspension recommendation,
  follow-up decisions on `needs_evidence`). The UI reads its actions from
  `src/features/workspace/decisionConfig.ts`; an endpoint such as
  `GET /api/v1/cases/{id}/decision-options` →
  `[{ "id": "escalate_state", "label": "…", "requires_approval": true, "ladder": ["…"] }]`
  would let the bar render exactly what the case allows.
- `case.status !== "open"` locks the bar, but the backend accepts follow-up decisions; a
  `case.can_decide` flag would remove the guess.

## Auth

- `GET /api/v1/auth/me` answers 401 before login, which the browser logs as a console error on
  the landing and login pages. A `200 { "user": null }` would keep the console clean.
