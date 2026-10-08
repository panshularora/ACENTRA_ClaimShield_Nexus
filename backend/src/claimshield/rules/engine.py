from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

import pandas as pd

from claimshield.synth.codes import PTP_PAIRS, UNIT_CAPS


@dataclass
class AlertDraft:
    detector: str
    rule_id: str
    rule_version: int
    entity_id: str
    entity_type: str
    line_ids: list[str]
    score: float
    evidence: dict[str, Any] = field(default_factory=dict)


def evaluate_rules(tables: dict[str, pd.DataFrame]) -> list[AlertDraft]:
    alerts: list[AlertDraft] = []
    alerts.extend(_duplicates(tables))
    alerts.extend(_ptp(tables))
    alerts.extend(_unit_caps(tables))
    alerts.extend(_after_death(tables))
    alerts.extend(_daily_minutes(tables))
    alerts.extend(_inpatient_overlap(tables))
    alerts.extend(_evv_missing(tables))
    alerts.extend(_excluded(tables))
    alerts.extend(_doctor_shopping(tables))
    alerts.extend(_sex_implausible(tables))
    alerts.extend(_pos_mismatch(tables))
    alerts.extend(_ambulance_overlap(tables))
    alerts.extend(_clone_billing(tables))
    return alerts


def _duplicates(tables: dict[str, pd.DataFrame]) -> list[AlertDraft]:
    lines = tables["claim_line"].copy()
    claims = tables["claim"][["claim_id", "member_id", "billing_provider_id"]]
    merged = lines.merge(claims, on="claim_id")
    grouped = merged.groupby(
        ["member_id", "billing_provider_id", "code", "dos_from"], dropna=False
    )
    out: list[AlertDraft] = []
    for key, grp in grouped:
        if len(grp) < 2:
            continue
        out.append(
            AlertDraft(
                detector="rules",
                rule_id="R-DUP-001",
                rule_version=1,
                entity_id=str(key[1]),
                entity_type="provider",
                line_ids=grp["line_id"].tolist(),
                score=1.0,
                evidence={"kind": "duplicate", "member_id": str(key[0]), "dos": str(key[3])},
            )
        )
    return out


def _ptp(tables: dict[str, pd.DataFrame]) -> list[AlertDraft]:
    lines = tables["claim_line"].merge(tables["claim"][["claim_id", "member_id", "billing_provider_id"]], on="claim_id")
    out: list[AlertDraft] = []
    for col1, col2, indicator in PTP_PAIRS:
        if indicator != 0:
            continue
        left = lines[lines.code == col1]
        right = lines[lines.code == col2]
        joined = left.merge(
            right,
            on=["member_id", "billing_provider_id", "dos_from"],
            suffixes=("_a", "_b"),
        )
        for _, row in joined.iterrows():
            out.append(
                AlertDraft(
                    detector="rules",
                    rule_id="R-PTP-001",
                    rule_version=1,
                    entity_id=str(row.billing_provider_id),
                    entity_type="provider",
                    line_ids=[row.line_id_a, row.line_id_b],
                    score=1.0,
                    evidence={"kind": "ptp_pair", "column1": col1, "column2": col2},
                )
            )
    return out


def _unit_caps(tables: dict[str, pd.DataFrame]) -> list[AlertDraft]:
    out: list[AlertDraft] = []
    lines = tables["claim_line"].merge(tables["claim"][["claim_id", "billing_provider_id"]], on="claim_id")
    for code, cap in UNIT_CAPS.items():
        hit = lines[(lines.code == code) & (lines.units > cap)]
        for _, row in hit.iterrows():
            out.append(
                AlertDraft(
                    detector="rules",
                    rule_id="R-UNIT-001",
                    rule_version=1,
                    entity_id=str(row.billing_provider_id),
                    entity_type="provider",
                    line_ids=[row.line_id],
                    score=1.0,
                    evidence={"kind": "unit_cap", "code": code, "units": float(row.units), "cap": cap},
                )
            )
    return out


def _after_death(tables: dict[str, pd.DataFrame]) -> list[AlertDraft]:
    members = tables["member"]
    dead = members[members["date_of_death"].notna()]
    if dead.empty:
        return []
    lines = tables["claim_line"].merge(tables["claim"][["claim_id", "member_id", "billing_provider_id"]], on="claim_id")
    merged = lines.merge(dead[["member_id", "date_of_death"]], on="member_id")
    merged["date_of_death"] = pd.to_datetime(merged["date_of_death"]).dt.date
    merged["dos_from"] = pd.to_datetime(merged["dos_from"]).dt.date
    hit = merged[merged["dos_from"] > merged["date_of_death"]]
    out = []
    for _, row in hit.iterrows():
        out.append(
            AlertDraft(
                detector="rules",
                rule_id="R-DEATH-001",
                rule_version=1,
                entity_id=str(row.billing_provider_id),
                entity_type="provider",
                line_ids=[row.line_id],
                score=1.0,
                evidence={"kind": "after_death", "member_id": row.member_id, "dod": str(row.date_of_death)},
            )
        )
    return out


def _daily_minutes(tables: dict[str, pd.DataFrame]) -> list[AlertDraft]:
    lines = tables["claim_line"].copy()
    lines["minutes"] = lines["minutes"].fillna(0)
    grouped = lines.groupby(["rendering_provider_id", "dos_from"], dropna=False)["minutes"].sum()
    out = []
    for (prov, dos), total in grouped.items():
        if total > 960:
            subset = lines[(lines.rendering_provider_id == prov) & (lines.dos_from == dos)]
            out.append(
                AlertDraft(
                    detector="rules",
                    rule_id="R-BH-001",
                    rule_version=1,
                    entity_id=str(prov),
                    entity_type="provider",
                    line_ids=subset["line_id"].tolist(),
                    score=1.0,
                    evidence={"kind": "daily_minutes_cap", "minutes": float(total), "max_minutes": 960},
                )
            )
    return out


def _inpatient_overlap(tables: dict[str, pd.DataFrame]) -> list[AlertDraft]:
    stays = tables.get("inpatient_stay")
    if stays is None or stays.empty:
        return []
    claims = tables["claim"][["claim_id", "member_id", "billing_provider_id"]]
    lines = tables["claim_line"].merge(claims, on="claim_id")
    lines["dos_from"] = pd.to_datetime(lines["dos_from"]).dt.date
    stays = stays.copy()
    stays["admit"] = pd.to_datetime(stays["admit"]).dt.date
    stays["discharge"] = pd.to_datetime(stays["discharge"]).dt.date
    out = []
    for _, stay in stays.iterrows():
        mask = (
            (lines.member_id == stay.member_id)
            & (lines.dos_from >= stay.admit)
            & (lines.dos_from <= stay.discharge)
            & (~lines.pos.isin(["21", "23"]))
        )
        hit = lines[mask]
        if hit.empty:
            continue
        out.append(
            AlertDraft(
                detector="rules",
                rule_id="R-IP-001",
                rule_version=1,
                entity_id=str(hit.iloc[0].billing_provider_id),
                entity_type="provider",
                line_ids=hit["line_id"].tolist(),
                score=1.0,
                evidence={"kind": "inpatient_overlap", "member_id": stay.member_id},
            )
        )
    return out


def _evv_missing(tables: dict[str, pd.DataFrame]) -> list[AlertDraft]:
    claims = tables["claim"]
    hh = claims[claims.claim_type == "home_health"]
    if hh.empty:
        return []
    lines = tables["claim_line"].merge(hh[["claim_id", "member_id", "billing_provider_id"]], on="claim_id")
    evv = tables["evv_visit"]
    if evv.empty:
        covered = set()
    else:
        evv = evv.copy()
        evv["day"] = pd.to_datetime(evv["start_ts"]).dt.date
        covered = set(zip(evv["member_id"], evv["day"], strict=False))
    lines["dos_from"] = pd.to_datetime(lines["dos_from"]).dt.date
    out = []
    for _, row in lines.iterrows():
        key = (row.member_id, row.dos_from)
        if key in covered:
            continue
        out.append(
            AlertDraft(
                detector="rules",
                rule_id="R-EVV-001",
                rule_version=1,
                entity_id=str(row.billing_provider_id),
                entity_type="provider",
                line_ids=[row.line_id],
                score=0.9,
                evidence={"kind": "evv_missing", "member_id": row.member_id},
            )
        )
    return out


def _excluded(tables: dict[str, pd.DataFrame]) -> list[AlertDraft]:
    excl = tables["exclusion_record"]
    npis = set(excl["npi"].dropna().astype(str))
    if not npis:
        return []
    providers = tables["provider"]
    flagged = providers[providers.npi_syn.astype(str).isin(npis)]
    if flagged.empty:
        return []
    claims = tables["claim"]
    lines = tables["claim_line"].merge(claims[["claim_id", "billing_provider_id"]], on="claim_id")
    out = []
    for _, prov in flagged.iterrows():
        hit = lines[lines.billing_provider_id == prov.provider_id]
        if hit.empty:
            continue
        out.append(
            AlertDraft(
                detector="rules",
                rule_id="R-LEIE-001",
                rule_version=1,
                entity_id=str(prov.provider_id),
                entity_type="provider",
                line_ids=hit["line_id"].tolist()[:25],
                score=1.0,
                evidence={"kind": "excluded_party", "npi": prov.npi_syn},
            )
        )
    return out


def _doctor_shopping(tables: dict[str, pd.DataFrame]) -> list[AlertDraft]:
    rx = tables.get("rx_fill")
    if rx is None or rx.empty:
        return []
    opioids = rx[(rx.drug_class_syn == "opioid") & (rx.mme >= 120)]
    out = []
    for member_id, grp in opioids.groupby("member_id"):
        if grp["prescriber_id"].nunique() >= 4 and grp["pharmacy_id"].nunique() >= 4:
            out.append(
                AlertDraft(
                    detector="rules",
                    rule_id="R-RX-001",
                    rule_version=1,
                    entity_id=str(grp.iloc[0].prescriber_id),
                    entity_type="provider",
                    line_ids=[],
                    score=0.85,
                    evidence={
                        "kind": "doctor_shopping",
                        "member_id": member_id,
                        "prescribers": int(grp["prescriber_id"].nunique()),
                        "pharmacies": int(grp["pharmacy_id"].nunique()),
                    },
                )
            )
    return out


def _sex_implausible(tables: dict[str, pd.DataFrame]) -> list[AlertDraft]:
    members = tables["member"][["member_id", "sex"]]
    lines = tables["claim_line"].merge(tables["claim"][["claim_id", "member_id", "billing_provider_id"]], on="claim_id")
    lines = lines.merge(members, on="member_id")
    hit = lines[(lines.code == "PROC-MALE-01") & (lines.sex == "F")]
    out = []
    for _, row in hit.iterrows():
        out.append(
            AlertDraft(
                detector="rules",
                rule_id="R-SEX-001",
                rule_version=1,
                entity_id=str(row.billing_provider_id),
                entity_type="provider",
                line_ids=[row.line_id],
                score=1.0,
                evidence={"kind": "sex_implausible", "member_id": row.member_id},
            )
        )
    return out


def _pos_mismatch(tables: dict[str, pd.DataFrame]) -> list[AlertDraft]:
    lines = tables["claim_line"].merge(
        tables["claim"][["claim_id", "billing_provider_id"]], on="claim_id"
    )
    office_codes = {f"EM-EST-{i}" for i in range(1, 6)}
    hit = lines[lines.code.isin(office_codes) & lines.pos.isin(["21", "23", "41"])]
    out: list[AlertDraft] = []
    for _, row in hit.iterrows():
        out.append(
            AlertDraft(
                detector="rules",
                rule_id="R-POS-001",
                rule_version=1,
                entity_id=str(row.billing_provider_id),
                entity_type="provider",
                line_ids=[row.line_id],
                score=0.8,
                evidence={"kind": "pos_mismatch", "code": row.code, "pos": row.pos},
            )
        )
    return out


def _ambulance_overlap(tables: dict[str, pd.DataFrame]) -> list[AlertDraft]:
    lines = tables["claim_line"].copy()
    amb = lines[lines.code.isin(["A0425", "A0427"])]
    if amb.empty:
        return []
    grouped = amb.groupby(["rendering_provider_id", "dos_from"], dropna=False)
    out: list[AlertDraft] = []
    for (prov, dos), grp in grouped:
        minutes = float(grp["minutes"].fillna(0).sum())
        if len(grp) >= 2 and minutes >= 90:
            out.append(
                AlertDraft(
                    detector="rules",
                    rule_id="R-AMB-001",
                    rule_version=1,
                    entity_id=str(prov),
                    entity_type="provider",
                    line_ids=grp["line_id"].tolist(),
                    score=1.0,
                    evidence={
                        "kind": "ambulance_overlap",
                        "trips": int(len(grp)),
                        "minutes": minutes,
                        "dos": str(dos),
                    },
                )
            )
    return out


def _clone_billing(tables: dict[str, pd.DataFrame]) -> list[AlertDraft]:
    claims = tables["claim"][["claim_id", "member_id", "billing_provider_id"]]
    lines = tables["claim_line"].merge(claims, on="claim_id")
    grouped = lines.groupby(
        ["billing_provider_id", "dos_from", "code", "paid"], dropna=False
    )
    out: list[AlertDraft] = []
    for key, grp in grouped:
        if grp["member_id"].nunique() < 8:
            continue
        out.append(
            AlertDraft(
                detector="rules",
                rule_id="R-CLONE-001",
                rule_version=1,
                entity_id=str(key[0]),
                entity_type="provider",
                line_ids=grp["line_id"].tolist(),
                score=0.9,
                evidence={
                    "kind": "clone_billing",
                    "members": int(grp["member_id"].nunique()),
                    "code": str(key[2]),
                    "paid": float(key[3]),
                },
            )
        )
    return out
