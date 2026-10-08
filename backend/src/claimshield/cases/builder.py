from __future__ import annotations

from collections import defaultdict

import pandas as pd

from claimshield.core.ids import new_id
from claimshield.rules.engine import AlertDraft


def build_cases(
    alerts: list[AlertDraft],
    tables: dict[str, pd.DataFrame],
    communities: dict[str, int],
) -> list[dict]:
    groups: dict[str, list[AlertDraft]] = defaultdict(list)
    for alert in alerts:
        comm = communities.get(alert.entity_id)
        key = f"comm:{comm}" if comm is not None else f"ent:{alert.entity_id}"
        groups[key].append(alert)

    claims = tables["claim"]
    lines = tables["claim_line"]
    paid_by_line = lines.set_index("line_id")["paid"].to_dict()
    cases = []
    for key, group in groups.items():
        entity_id = group[0].entity_id
        line_ids = [lid for a in group for lid in a.line_ids]
        dollars = float(sum(paid_by_line.get(lid, 0.0) for lid in line_ids))
        members = set()
        if line_ids:
            hit = lines[lines.line_id.isin(line_ids)].merge(claims[["claim_id", "member_id"]], on="claim_id")
            members = set(hit["member_id"].tolist())
        kinds = {a.evidence.get("kind") for a in group}
        harm = 4 if "after_death" in kinds or "excluded_party" in kinds else (2 if len(group) > 3 else 1)
        severity = 4 if "after_death" in kinds else (3 if "duplicate" in kinds or "ptp_pair" in kinds else 2)
        evidence = min(1.0, 0.35 + 0.15 * len({a.rule_id for a in group}))
        cases.append(
            {
                "case_id": new_id("CASE"),
                "primary_entity_id": entity_id,
                "primary_entity_type": "provider",
                "alert_count": len(group),
                "line_ids": line_ids,
                "members_affected": len(members),
                "flagged_dollars": round(dollars, 2),
                "harm": harm,
                "severity": severity,
                "evidence_strength": round(evidence, 3),
                "estimated_hours": 6.0 + 0.4 * len(group),
                "p_confirm": round(min(0.95, evidence), 3),
                "lane": "harm_priority" if harm >= 4 else ("needs_evidence" if evidence < 0.4 else "selected"),
                "alerts": group,
                "group_key": key,
            }
        )
    return cases
