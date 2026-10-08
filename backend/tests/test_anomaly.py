import pandas as pd

from claimshield.anomaly.peer import evaluate_anomalies, select_peer_group


def _providers(n_urban: int, n_rural: int, specialty: str = "family_medicine") -> pd.DataFrame:
    rows = []
    for i in range(n_urban):
        rows.append(
            {
                "provider_id": f"PU{i:03d}",
                "specialty": specialty,
                "kind": "professional",
                "rural": False,
                "service_line": "professional",
                "location_id": "LOC-U",
            }
        )
    for i in range(n_rural):
        rows.append(
            {
                "provider_id": f"PR{i:03d}",
                "specialty": specialty,
                "kind": "professional",
                "rural": True,
                "service_line": "professional",
                "location_id": "LOC-R",
            }
        )
    return pd.DataFrame(rows)


def test_rural_cell_is_not_auto_flagged_when_peers_are_few() -> None:
    providers = _providers(n_urban=12, n_rural=2)
    group = select_peer_group(providers, "PR000")
    assert group["geography"] == "rural"
    assert group["n_peers"] >= 8 or group["confidence"] in {"limited", "insufficient"}
    close = providers[
        (providers.specialty == "family_medicine")
        & (providers.kind == "professional")
        & (providers.rural == True)  # noqa: E712
        & (providers.provider_id != "PR000")
    ]
    assert len(close) == 1
    assert "rural" not in group["dimensions_used"] or group["n_peers"] >= 8


def test_em_flag_includes_peer_range_and_skips_tiny_cells() -> None:
    providers = _providers(14, 1)
    claim_rows = []
    line_rows = []
    cid = 0
    for _, prov in providers.iterrows():
        pid = prov.provider_id
        for _ in range(20):
            cid += 1
            claim_id = f"CL{cid}"
            claim_rows.append({"claim_id": claim_id, "billing_provider_id": pid, "claim_type": "professional"})
            code = "EM-EST-5" if pid == "PU000" else "EM-EST-3"
            line_rows.append({"line_id": f"LN{cid}", "claim_id": claim_id, "code": code, "paid": 100.0})
    tables = {
        "provider": providers,
        "claim": pd.DataFrame(claim_rows),
        "claim_line": pd.DataFrame(line_rows),
    }
    alerts = evaluate_anomalies(tables)
    em = [a for a in alerts if a.rule_id == "A-EM-001"]
    assert any(a.entity_id == "PU000" for a in em)
    hit = next(a for a in em if a.entity_id == "PU000")
    assert hit.evidence["approach"] == "behavioral_anomaly"
    assert "peer_median" in hit.evidence
    assert hit.evidence["peer_group"]["n_peers"] >= 8
    assert "PR000" not in {a.entity_id for a in em}
