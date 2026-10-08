# Case network API (schema version 2)

`GET /api/v1/cases/{case_id}/network` returns the case's parties and their surroundings, up to two relationship hops from the case subjects. Every node and edge says why it is there. Roles need `case:read`. Member identifiers are masked unless the caller holds `member:unmask` and has asked for unmasking.

The source of truth is `backend/src/claimshield/cases/network_models.py` (Pydantic). The example below is a real response from a fresh SQLite database seeded with `POST /api/v1/batches {"profile":"tiny","seed":7}` on `fix/backend-p0` (case `CASE-KRL8YA74EZ`, a priority-override case). Ids change from one database to the next.

## Response shape

```
NetworkPack {
  schema_version: 2
  case_id: str
  hops: int                       # 2
  primary_entity_id: str          # provider id, or member id for member-level cases
  subject_ids: [str]              # case parties (case.entity_ids)
  masked: bool                    # member labels masked for this caller
  nodes: [NetworkNode]
  edges: [NetworkEdge]
  limits: { hops, referral_top_n, max_providers (40), max_members (25),
            providers_shown, providers_dropped, members_total, members_shown }
}

NetworkNode {
  id: str
  type: "provider" | "member" | "facility" | "owner" | "address"
  label: str
  primary: bool                   # the case's primary entity
  is_subject: bool                # in case.entity_ids
  in_case: bool                   # subject, or on the case's flagged claim lines
  hop: int                        # 0 subject, 1-2 hops out
  alert_ids: [str]                # this case's alerts that name the node
  rule_ids: [str]
  n_flagged_lines: int
  flagged_paid: float             # paid $ on this case's flagged lines touching the node
  detail_path: str                # GET for claims and findings of the node in this case
  risk: float | null              # case priority score, primary node only
  harm: int | null                # case beneficiary-harm level 0-4, subject nodes only
  severity: int | null            # case severity 1-4, subject nodes only
  specialty, masked, owner_kind, facility_type: optional display fields
}

NetworkEdge {
  id: str                         # "<kind>:<source>:<target>", stable
  source: str
  target: str
  kind: "billed" | "rendered" | "at_facility" | "owns" | "referral" | "located_at"
        | "shared_tin" | "shared_contact" | "prescribed" | "dispensed"
  directed: bool                  # source -> target has meaning
  direction: "out" | "none"       # never "in"; "out" == directed
  inferred: bool                  # true for shared_tin / shared_contact (shared identifier, not a recorded relationship)
  count: int                      # records behind the edge (referrals, claim lines; 1 for a shared identifier)
  weight: float                   # count / max count of the same kind, (0, 1]
  label: str
  in_case: bool                   # an alert in this case relies on the edge, or it joins case parties
  evidence_ids: [str]             # "alert:<id>", "claim:<id>", "line:<id>"; capped at 50; resolvable at /cases/{id}/evidence/{evidence_id}
  evidence: {
    alert_ids, rule_ids, claim_ids, line_ids: [str]
    referral_ids: [int]
    attribute: { kind: "phone"|"email"|"bank_token"|"tin"|"address", value_masked: str } | null
    ownership_pct: float | null
    first_date, last_date: "YYYY-MM-DD" | null
    paid: float | null
  }
}
```

Fields that would be `null` (`risk`, `harm`, `severity`, `specialty`, `attribute`, …) are omitted from the JSON (`response_model_exclude_none`), so read them as optional.

Modelling choices:

- Shared practice addresses are one `address` hub node plus `located_at` edges, not a provider clique.
- Referrals keep direction (`source` = referrer, `target` = receiver) and volume (`count`). Only the top referral partners per provider are kept (`limits.referral_top_n`).
- `owns` goes owner -> provider and carries `ownership_pct`.
- `shared_contact` and `shared_tin` join two providers that share a phone, email, bank token or TIN. The value is masked in `evidence.attribute`.
- Member-level cases (doctor shopping) have a member subject. `prescribed` edges go prescriber -> member and `dispensed` edges go pharmacy -> member.
- Each edge is also an evidence item: `GET /api/v1/cases/{id}/evidence/edge:<edge id>` resolves it, so brief sentences can cite graph links.

## Related endpoints

- `GET /api/v1/cases/{case_id}/network/nodes/{node_id}` (the node's `detail_path`) returns `NodeDetail {case_id, node, profile, alerts, claim_lines, connections}`: the case's alerts and flagged lines that involve the node.
- `GET /api/v1/entities/{entity_id}/summary?case_id=` returns `EntitySummary {entity_id, case_id, node, profile, claims: {n_lines, paid, first_dos, last_dos, sample}, alerts, cases: [{case_id, status, lane, primary_entity_id, is_primary}], case_claim_lines, connections}`. It covers every claim line on file for the entity, not only the case's flagged lines. It answers 404 when the entity is not in that case's network, so it cannot be used to browse arbitrary providers.
- `GET /api/v1/cases/{case_id}/decision-options` returns what the decision bar may offer the caller for this case (example below).
- `GET /api/v1/auth/session` always answers 200: `{"authenticated": false, "user": null, "refresh_available": false}` before login, and `{"authenticated": true, "user": {...}, "refresh_available": true}` after. `GET /api/v1/auth/me` still answers 401 when signed out, because the current client treats any 200 from `/me` as a signed-in user.

## Example: `GET /api/v1/cases/CASE-KRL8YA74EZ/network`

```json
{
  "schema_version": 2,
  "case_id": "CASE-KRL8YA74EZ",
  "hops": 2,
  "primary_entity_id": "PRV-YHCS7YKNYQ",
  "subject_ids": [
    "PRV-YHCS7YKNYQ"
  ],
  "masked": true,
  "nodes": [
    {
      "id": "OWN-6NXS4ZTRZS",
      "type": "owner",
      "label": "Johnson Inc",
      "primary": false,
      "is_subject": false,
      "in_case": false,
      "hop": 0,
      "alert_ids": [],
      "rule_ids": [],
      "n_flagged_lines": 0,
      "flagged_paid": 0.0,
      "detail_path": "/api/v1/cases/CASE-KRL8YA74EZ/network/nodes/OWN-6NXS4ZTRZS",
      "owner_kind": "org"
    },
    {
      "id": "PRV-YHCS7YKNYQ",
      "type": "provider",
      "label": "Mejia-Anderson",
      "primary": true,
      "is_subject": true,
      "in_case": true,
      "hop": 0,
      "alert_ids": [
        "ALRT-KHT989IRH9"
      ],
      "rule_ids": [
        "R-IP-001"
      ],
      "n_flagged_lines": 3,
      "flagged_paid": 386.48,
      "detail_path": "/api/v1/cases/CASE-KRL8YA74EZ/network/nodes/PRV-YHCS7YKNYQ",
      "risk": 0.258,
      "harm": 4,
      "severity": 3,
      "specialty": "sud_clinic"
    },
    {
      "id": "addr:LOC-AU2Z3WE5P5",
      "type": "address",
      "label": "45957 DARRELL OVAL SUITE 774, 11758",
      "primary": false,
      "is_subject": false,
      "in_case": false,
      "hop": 1,
      "alert_ids": [],
      "rule_ids": [],
      "n_flagged_lines": 0,
      "flagged_paid": 0.0,
      "detail_path": "/api/v1/cases/CASE-KRL8YA74EZ/network/nodes/addr%3ALOC-AU2Z3WE5P5"
    },
    {
      "id": "MBR-59N7KMSMAY",
      "type": "member",
      "label": "Member \u00b7SMAY",
      "primary": false,
      "is_subject": false,
      "in_case": true,
      "hop": 1,
      "alert_ids": [
        "ALRT-KHT989IRH9"
      ],
      "rule_ids": [
        "R-IP-001"
      ],
      "n_flagged_lines": 1,
      "flagged_paid": 107.59,
      "detail_path": "/api/v1/cases/CASE-KRL8YA74EZ/network/nodes/MBR-59N7KMSMAY",
      "masked": true
    },
    {
      "id": "MBR-LYUPA4MC8N",
      "type": "member",
      "label": "Member \u00b7MC8N",
      "primary": false,
      "is_subject": false,
      "in_case": true,
      "hop": 1,
      "alert_ids": [
        "ALRT-KHT989IRH9"
      ],
      "rule_ids": [
        "R-IP-001"
      ],
      "n_flagged_lines": 1,
      "flagged_paid": 134.75,
      "detail_path": "/api/v1/cases/CASE-KRL8YA74EZ/network/nodes/MBR-LYUPA4MC8N",
      "masked": true
    },
    {
      "id": "MBR-SMLQ7MHU28",
      "type": "member",
      "label": "Member \u00b7HU28",
      "primary": false,
      "is_subject": false,
      "in_case": true,
      "hop": 1,
      "alert_ids": [
        "ALRT-KHT989IRH9"
      ],
      "rule_ids": [
        "R-IP-001"
      ],
      "n_flagged_lines": 1,
      "flagged_paid": 144.14,
      "detail_path": "/api/v1/cases/CASE-KRL8YA74EZ/network/nodes/MBR-SMLQ7MHU28",
      "masked": true
    },
    {
      "id": "PRV-AEV55VW98C",
      "type": "provider",
      "label": "Joshua Fowler",
      "primary": false,
      "is_subject": false,
      "in_case": false,
      "hop": 1,
      "alert_ids": [],
      "rule_ids": [],
      "n_flagged_lines": 0,
      "flagged_paid": 0.0,
      "detail_path": "/api/v1/cases/CASE-KRL8YA74EZ/network/nodes/PRV-AEV55VW98C",
      "specialty": "ground_ambulance"
    },
    {
      "id": "PRV-E2KQR2ZK3Q",
      "type": "provider",
      "label": "Ochoa, Lee and Henson",
      "primary": false,
      "is_subject": false,
      "in_case": false,
      "hop": 1,
      "alert_ids": [],
      "rule_ids": [],
      "n_flagged_lines": 0,
      "flagged_paid": 0.0,
      "detail_path": "/api/v1/cases/CASE-KRL8YA74EZ/network/nodes/PRV-E2KQR2ZK3Q",
      "specialty": "retail_pharmacy"
    },
    {
      "id": "PRV-GG7BBL7G9L",
      "type": "provider",
      "label": "Austin Howard",
      "primary": false,
      "is_subject": false,
      "in_case": false,
      "hop": 1,
      "alert_ids": [],
      "rule_ids": [],
      "n_flagged_lines": 0,
      "flagged_paid": 0.0,
      "detail_path": "/api/v1/cases/CASE-KRL8YA74EZ/network/nodes/PRV-GG7BBL7G9L",
      "specialty": "clinical_lab"
    },
    {
      "id": "PRV-HC5CWNTSHD",
      "type": "provider",
      "label": "Gutierrez-Smith",
      "primary": false,
      "is_subject": false,
      "in_case": false,
      "hop": 1,
      "alert_ids": [],
      "rule_ids": [],
      "n_flagged_lines": 0,
      "flagged_paid": 0.0,
      "detail_path": "/api/v1/cases/CASE-KRL8YA74EZ/network/nodes/PRV-HC5CWNTSHD",
      "specialty": "internal_medicine"
    },
    {
      "id": "PRV-Z84M5CG5BX",
      "type": "provider",
      "label": "Turner Inc",
      "primary": false,
      "is_subject": false,
      "in_case": false,
      "hop": 1,
      "alert_ids": [],
      "rule_ids": [],
      "n_flagged_lines": 0,
      "flagged_paid": 0.0,
      "detail_path": "/api/v1/cases/CASE-KRL8YA74EZ/network/nodes/PRV-Z84M5CG5BX",
      "specialty": "retail_pharmacy"
    }
  ],
  "edges": [
    {
      "id": "billed:PRV-YHCS7YKNYQ:MBR-59N7KMSMAY",
      "source": "PRV-YHCS7YKNYQ",
      "target": "MBR-59N7KMSMAY",
      "kind": "billed",
      "directed": true,
      "direction": "out",
      "inferred": false,
      "count": 1,
      "weight": 1.0,
      "label": "billed flagged service \u00d71",
      "in_case": true,
      "evidence_ids": [
        "alert:ALRT-KHT989IRH9",
        "claim:CLM-25E2NA2ACV",
        "line:LN-S6SLDEARYU"
      ],
      "evidence": {
        "alert_ids": [
          "ALRT-KHT989IRH9"
        ],
        "rule_ids": [
          "R-IP-001"
        ],
        "claim_ids": [
          "CLM-25E2NA2ACV"
        ],
        "line_ids": [
          "LN-S6SLDEARYU"
        ],
        "referral_ids": [],
        "first_date": "2024-02-12",
        "last_date": "2024-02-12",
        "paid": 107.59
      }
    },
    {
      "id": "billed:PRV-YHCS7YKNYQ:MBR-LYUPA4MC8N",
      "source": "PRV-YHCS7YKNYQ",
      "target": "MBR-LYUPA4MC8N",
      "kind": "billed",
      "directed": true,
      "direction": "out",
      "inferred": false,
      "count": 1,
      "weight": 1.0,
      "label": "billed flagged service \u00d71",
      "in_case": true,
      "evidence_ids": [
        "alert:ALRT-KHT989IRH9",
        "claim:CLM-MSQ53TCA5Q",
        "line:LN-C88PN67X4H"
      ],
      "evidence": {
        "alert_ids": [
          "ALRT-KHT989IRH9"
        ],
        "rule_ids": [
          "R-IP-001"
        ],
        "claim_ids": [
          "CLM-MSQ53TCA5Q"
        ],
        "line_ids": [
          "LN-C88PN67X4H"
        ],
        "referral_ids": [],
        "first_date": "2024-08-22",
        "last_date": "2024-08-22",
        "paid": 134.75
      }
    },
    {
      "id": "billed:PRV-YHCS7YKNYQ:MBR-SMLQ7MHU28",
      "source": "PRV-YHCS7YKNYQ",
      "target": "MBR-SMLQ7MHU28",
      "kind": "billed",
      "directed": true,
      "direction": "out",
      "inferred": false,
      "count": 1,
      "weight": 1.0,
      "label": "billed flagged service \u00d71",
      "in_case": true,
      "evidence_ids": [
        "alert:ALRT-KHT989IRH9",
        "claim:CLM-5BHW9RAX3G",
        "line:LN-SB4VSC4ZYQ"
      ],
      "evidence": {
        "alert_ids": [
          "ALRT-KHT989IRH9"
        ],
        "rule_ids": [
          "R-IP-001"
        ],
        "claim_ids": [
          "CLM-5BHW9RAX3G"
        ],
        "line_ids": [
          "LN-SB4VSC4ZYQ"
        ],
        "referral_ids": [],
        "first_date": "2024-02-23",
        "last_date": "2024-02-23",
        "paid": 144.14
      }
    },
    {
      "id": "located_at:PRV-E2KQR2ZK3Q:addr:LOC-AU2Z3WE5P5",
      "source": "PRV-E2KQR2ZK3Q",
      "target": "addr:LOC-AU2Z3WE5P5",
      "kind": "located_at",
      "directed": true,
      "direction": "out",
      "inferred": false,
      "count": 1,
      "weight": 1.0,
      "label": "practice address",
      "in_case": false,
      "evidence_ids": [],
      "evidence": {
        "alert_ids": [],
        "rule_ids": [],
        "claim_ids": [],
        "line_ids": [],
        "referral_ids": [],
        "attribute": {
          "kind": "address",
          "value_masked": "45957 DARRELL OVAL SUITE 774, 11758"
        }
      }
    },
    {
      "id": "located_at:PRV-GG7BBL7G9L:addr:LOC-AU2Z3WE5P5",
      "source": "PRV-GG7BBL7G9L",
      "target": "addr:LOC-AU2Z3WE5P5",
      "kind": "located_at",
      "directed": true,
      "direction": "out",
      "inferred": false,
      "count": 1,
      "weight": 1.0,
      "label": "practice address",
      "in_case": false,
      "evidence_ids": [],
      "evidence": {
        "alert_ids": [],
        "rule_ids": [],
        "claim_ids": [],
        "line_ids": [],
        "referral_ids": [],
        "attribute": {
          "kind": "address",
          "value_masked": "45957 DARRELL OVAL SUITE 774, 11758"
        }
      }
    },
    {
      "id": "owns:OWN-6NXS4ZTRZS:PRV-AEV55VW98C",
      "source": "OWN-6NXS4ZTRZS",
      "target": "PRV-AEV55VW98C",
      "kind": "owns",
      "directed": true,
      "direction": "out",
      "inferred": false,
      "count": 1,
      "weight": 1.0,
      "label": "owns 25%",
      "in_case": false,
      "evidence_ids": [],
      "evidence": {
        "alert_ids": [],
        "rule_ids": [],
        "claim_ids": [],
        "line_ids": [],
        "referral_ids": [],
        "ownership_pct": 25.0,
        "first_date": "2022-11-04",
        "last_date": "2022-11-04"
      }
    },
    {
      "id": "owns:OWN-6NXS4ZTRZS:PRV-E2KQR2ZK3Q",
      "source": "OWN-6NXS4ZTRZS",
      "target": "PRV-E2KQR2ZK3Q",
      "kind": "owns",
      "directed": true,
      "direction": "out",
      "inferred": false,
      "count": 1,
      "weight": 1.0,
      "label": "owns 100%",
      "in_case": false,
      "evidence_ids": [],
      "evidence": {
        "alert_ids": [],
        "rule_ids": [],
        "claim_ids": [],
        "line_ids": [],
        "referral_ids": [],
        "ownership_pct": 100.0,
        "first_date": "2023-11-04",
        "last_date": "2023-11-04"
      }
    },
    {
      "id": "owns:OWN-6NXS4ZTRZS:PRV-HC5CWNTSHD",
      "source": "OWN-6NXS4ZTRZS",
      "target": "PRV-HC5CWNTSHD",
      "kind": "owns",
      "directed": true,
      "direction": "out",
      "inferred": false,
      "count": 1,
      "weight": 1.0,
      "label": "owns 60%",
      "in_case": false,
      "evidence_ids": [],
      "evidence": {
        "alert_ids": [],
        "rule_ids": [],
        "claim_ids": [],
        "line_ids": [],
        "referral_ids": [],
        "ownership_pct": 60.0,
        "first_date": "2023-10-16",
        "last_date": "2023-10-16"
      }
    },
    {
      "id": "owns:OWN-6NXS4ZTRZS:PRV-YHCS7YKNYQ",
      "source": "OWN-6NXS4ZTRZS",
      "target": "PRV-YHCS7YKNYQ",
      "kind": "owns",
      "directed": true,
      "direction": "out",
      "inferred": false,
      "count": 1,
      "weight": 1.0,
      "label": "owns 25%",
      "in_case": false,
      "evidence_ids": [],
      "evidence": {
        "alert_ids": [],
        "rule_ids": [],
        "claim_ids": [],
        "line_ids": [],
        "referral_ids": [],
        "ownership_pct": 25.0,
        "first_date": "2023-05-11",
        "last_date": "2023-05-11"
      }
    },
    {
      "id": "referral:PRV-GG7BBL7G9L:PRV-YHCS7YKNYQ",
      "source": "PRV-GG7BBL7G9L",
      "target": "PRV-YHCS7YKNYQ",
      "kind": "referral",
      "directed": true,
      "direction": "out",
      "inferred": false,
      "count": 1,
      "weight": 0.5,
      "label": "referred \u00d71",
      "in_case": false,
      "evidence_ids": [],
      "evidence": {
        "alert_ids": [],
        "rule_ids": [],
        "claim_ids": [],
        "line_ids": [],
        "referral_ids": [
          19
        ],
        "first_date": "2024-04-07",
        "last_date": "2024-04-07"
      }
    },
    {
      "id": "referral:PRV-YHCS7YKNYQ:PRV-Z84M5CG5BX",
      "source": "PRV-YHCS7YKNYQ",
      "target": "PRV-Z84M5CG5BX",
      "kind": "referral",
      "directed": true,
      "direction": "out",
      "inferred": false,
      "count": 2,
      "weight": 1.0,
      "label": "referred \u00d72",
      "in_case": false,
      "evidence_ids": [],
      "evidence": {
        "alert_ids": [],
        "rule_ids": [],
        "claim_ids": [],
        "line_ids": [],
        "referral_ids": [
          129,
          2
        ],
        "first_date": "2024-06-28",
        "last_date": "2024-08-05"
      }
    }
  ],
  "limits": {
    "hops": 2,
    "referral_top_n": 5,
    "max_providers": 40,
    "max_members": 25,
    "providers_shown": 6,
    "providers_dropped": 0,
    "members_total": 3,
    "members_shown": 3
  }
}
```

## Example: entity summary (lists trimmed to one item)

`GET /api/v1/entities/PRV-2RBJKMU8EL/summary?case_id=CASE-2QC4VG0ZEJ`

```json
{
  "entity_id": "PRV-2RBJKMU8EL",
  "case_id": "CASE-2QC4VG0ZEJ",
  "node": {
    "id": "PRV-2RBJKMU8EL",
    "type": "provider",
    "label": "Angelica Joseph",
    "primary": false,
    "is_subject": false,
    "in_case": false,
    "hop": 1,
    "alert_ids": [],
    "rule_ids": [],
    "n_flagged_lines": 0,
    "flagged_paid": 0.0,
    "detail_path": "/api/v1/cases/CASE-2QC4VG0ZEJ/network/nodes/PRV-2RBJKMU8EL",
    "specialty": "ground_ambulance"
  },
  "profile": {
    "provider_id": "PRV-2RBJKMU8EL",
    "name": "Angelica Joseph",
    "npi_syn": "2589522800",
    "kind": "individual",
    "specialty": "ground_ambulance",
    "service_line": "ambulance",
    "enroll_date": "2023-05-05",
    "rural": false,
    "sole_community": false
  },
  "claims": {
    "n_lines": 49,
    "paid": 4613.61,
    "first_dos": "2024-01-01",
    "last_dos": "2024-08-23",
    "sample": [
      {
        "line_id": "LN-A2KAJLEEA8",
        "claim_id": "CLM-G4QA3F5U4G",
        "dos_from": "2024-07-24",
        "dos_to": "2024-07-24",
        "code": "A0425",
        "code_system": "HCPCS2",
        "modifiers": [],
        "units": 24.0,
        "minutes": null,
        "pos": "41",
        "charge": 205.28,
        "allowed": 168.33,
        "paid": 151.5,
        "rendering_provider_id": "PRV-2RBJKMU8EL",
        "ordering_provider_id": "PRV-2RBJKMU8EL",
        "billing_provider_id": "PRV-2RBJKMU8EL",
        "facility_id": null,
        "claim_type": "ambulance",
        "claim_status": "paid",
        "received_date": "2024-08-22",
        "adjudicated_date": "2024-09-03",
        "member": {
          "member_id": "MBR-W33FF9PGW5",
          "name": null,
          "display": "Member \u00b7PGW5",
          "masked": true
        },
        "signals": [],
        "source_system": "generator",
        "source_ref": null
      }
    ]
  },
  "alerts": [],
  "cases": [],
  "case_claim_lines": [],
  "connections": [
    {
      "id": "owns:OWN-9FAAXMZ5ZN:PRV-2RBJKMU8EL",
      "source": "OWN-9FAAXMZ5ZN",
      "target": "PRV-2RBJKMU8EL",
      "kind": "owns",
      "directed": true,
      "direction": "out",
      "inferred": false,
      "count": 1,
      "weight": 1.0,
      "label": "owns 100%",
      "in_case": false,
      "evidence_ids": [],
      "evidence": {
        "alert_ids": [],
        "rule_ids": [],
        "claim_ids": [],
        "line_ids": [],
        "referral_ids": [],
        "ownership_pct": 100.0,
        "first_date": "2023-05-05",
        "last_date": "2023-05-05"
      }
    }
  ]
}
```

## Example: decision options (manager, open unassigned case)

```json
{
  "case_id": "CASE-2QC4VG0ZEJ",
  "status": "open",
  "role": "manager",
  "can_decide": true,
  "blocked_reason": null,
  "allowed_actions": [
    "escalate",
    "monitor",
    "dismiss",
    "needs_evidence"
  ],
  "can_approve": false,
  "can_reopen": false,
  "pending_decision": null,
  "min_reason_chars": 20,
  "max_reason_chars": 4000,
  "options": [
    {
      "id": "needs_evidence",
      "label": "Request more evidence",
      "hint": "Keep the case open and request records; decide again when they arrive.",
      "requires_approval": false,
      "closes_case": false,
      "resulting_status": "needs_evidence",
      "default_step": "medical_records_request",
      "ladder": [
        {
          "step": "medical_records_request",
          "label": "Medical records request",
          "default": true,
          "requires_basis_on_approval": false
        }
      ],
      "enabled": true
    },
    {
      "id": "monitor",
      "label": "Monitor",
      "hint": "Keep the case open and watch for a recurrence; education letter by default.",
      "requires_approval": false,
      "closes_case": false,
      "resulting_status": "monitor",
      "default_step": "education_letter",
      "ladder": [
        {
          "step": "education_letter",
          "label": "Provider education letter",
          "default": true,
          "requires_basis_on_approval": false
        }
      ],
      "enabled": true
    },
    {
      "id": "escalate",
      "label": "Escalate to the State Medicaid agency",
      "hint": "Refer to the state program integrity unit. A manager must approve before the case closes.",
      "requires_approval": true,
      "closes_case": true,
      "resulting_status": "pending_approval",
      "default_step": "state_pi_referral",
      "ladder": [
        {
          "step": "state_pi_referral",
          "label": "Refer to the State Medicaid agency program integrity unit (for MFCU consideration)",
          "default": true,
          "requires_basis_on_approval": false
        },
        {
          "step": "prepayment_review",
          "label": "Recommend prepayment review (state or plan policy)",
          "default": false,
          "requires_basis_on_approval": false
        },
        {
          "step": "payment_suspension_recommend",
          "label": "Recommend that the State Medicaid agency consider a 42 CFR 455.23 payment suspension (state agency decision; good-cause exceptions may apply)",
          "default": false,
          "requires_basis_on_approval": true
        }
      ],
      "enabled": true
    },
    {
      "id": "dismiss",
      "label": "Dismiss with reason",
      "hint": "Evidence does not support concern. Closes the case; a manager can reopen it.",
      "requires_approval": false,
      "closes_case": true,
      "resulting_status": "dismissed",
      "default_step": null,
      "ladder": [],
      "enabled": true
    }
  ]
}
```

## Frontend changes needed

Mapped to `frontend/src/components/network/graphModel.ts` and `frontend/src/api/types.ts` on `origin/main`:

| Where | Change |
|---|---|
| `normaliseNode` `flaggedPaid` | Already reads `node.flagged_paid ?? node.flagged_dollars`; the API now sends only `flagged_paid` on nodes. Drop `flagged_dollars` from `NetworkNode` in `types.ts`. Case and queue rows keep `flagged_dollars`. |
| `normaliseNode` `riskLevel` | Read `node.severity` (sent on subject nodes) before falling back to `ctx.subjectSeverity`. |
| `normaliseNode` `harm`, `isSubject`, `inCase`, `alertIds`, `flaggedLines`, `hop` | Names already match (`harm`, `is_subject`, `in_case`, `alert_ids`, `n_flagged_lines`, `hop`). No change. |
| `normaliseEdges` | `id`, `direction` (`"out"`/`"none"`, never `"in"`), `count`, `evidence_ids`, `inferred` already match. Edge ids are unique, so the merge step becomes a no-op. |
| `DIRECTED_KINDS` / legend | New kinds: `prescribed`, `dispensed` (member-level cases), `billed`, `rendered`, `at_facility`, `located_at`, `shared_contact`. `type` never takes `phone`/`bank`: a shared phone or bank token is a `shared_contact` edge with `evidence.attribute.kind`. |
| Evidence ids | Edges cite `alert:`, `claim:` and `line:` ids, not `contact:`/`own:` ids. The edge itself resolves as `edge:<edge.id>` at `/cases/{id}/evidence/{item_id}`. |
| Selection card | Use `GET /api/v1/entities/{id}/summary?case_id=` for linked providers outside the case (claims, alerts, related cases). |
| Pagerank / community | Not sent (known gap). |
| `api/client.ts` `me()` | Probe `GET /api/v1/auth/session` before login (always 200) and keep `/me` for the signed-in user. `/me` still answers 401 when signed out. |
| Cookie writes | Every cookie-authenticated POST must send `X-CSRF-Token` equal to the `cs_csrf` cookie. A missing or wrong header is now a 401 ("csrf check failed"). |
| `decisionConfig.ts` | Render from `GET /cases/{id}/decision-options`. Ladders: `needs_evidence` -> `medical_records_request`; `monitor` -> `education_letter`; `escalate` -> `state_pi_referral` (default), `prepayment_review`, `payment_suspension_recommend`; `dismiss` -> none. `mfcu_referral` is no longer accepted, and `prepayment_review` under `monitor`/`needs_evidence` is a 422. |
| Decision results | `escalate` returns `status: "pending_approval"` with no `proposal`. Approve with `POST /decisions/{id}:approve {note}` (note of 20+ characters for `payment_suspension_recommend`), which returns `{decision, case_id, status, audit, proposal, label, note}`, not `{decision_id, proposal, page}`. Reject with `POST /decisions/{id}:reject {note}` (20+ characters). Managers reopen with `POST /cases/{id}/reopen {reason}`. Cases carry `can_decide`, `pending_decision`, `allowed_actions` and `decision_blocked_reason`. |
| `ProposalCard.tsx` | Read `body.observed_pattern` (was `confirmed_pattern`), plus `pattern_status` and `decision_context`. |
| Queue and run summary | Lane key stays `harm_priority`; show `lane_label` ("Priority override…") and `priority_override` / `override_kinds`. Capacity is `run.summary.capacity {capacity_hours, priority_override_hours, selected_hours, capacity_used_hours, over_capacity_hours, override_share, override_share_warning, needs_evidence_hours}`. There is no `harm_reserved_hours`. `expected_value` is now dollars only. |
| Case header | `primary_entity_type` can be `"member"` (doctor-shopping cases). |
