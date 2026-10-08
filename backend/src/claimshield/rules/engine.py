from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from claimshield.rules import leie
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
    related_entity_ids: list[str] = field(default_factory=list)


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
    alerts.extend(_stay_compression(tables))
    alerts.extend(_mileage_padding(tables))
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
        for prov, grp in hit.groupby("billing_provider_id"):
            out.append(
                AlertDraft(
                    detector="rules",
                    rule_id="R-UNIT-001",
                    rule_version=1,
                    entity_id=str(prov),
                    entity_type="provider",
                    line_ids=grp["line_id"].tolist()[:40],
                    score=1.0,
                    evidence={
                        "kind": "unit_cap",
                        "code": code,
                        "n_lines": int(len(grp)),
                        "max_units": float(grp["units"].max()),
                        "cap": cap,
                    },
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
    out: list[AlertDraft] = []
    for prov, grp in hit.groupby("billing_provider_id"):
        out.append(
            AlertDraft(
                detector="rules",
                rule_id="R-DEATH-001",
                rule_version=1,
                entity_id=str(prov),
                entity_type="provider",
                line_ids=grp["line_id"].tolist()[:40],
                score=1.0,
                evidence={
                    "kind": "after_death",
                    "n_lines": int(len(grp)),
                    "member_ids": sorted({str(m) for m in grp["member_id"].tolist()})[:8],
                    "dod": str(grp.iloc[0]["date_of_death"]),
                },
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
    claims = tables["claim"][["claim_id", "member_id", "billing_provider_id", "claim_type"]]
    lines = tables["claim_line"].merge(claims, on="claim_id")
    community = {"home_health", "behavioral_health"}
    lines = lines[lines.claim_type.isin(community) | lines.code.isin(["ABA-60", "PSY-60", "HH-VISIT"])]
    if lines.empty:
        return []
    lines["dos_from"] = pd.to_datetime(lines["dos_from"]).dt.date
    stays = stays.copy()
    stays["admit"] = pd.to_datetime(stays["admit"]).dt.date
    stays["discharge"] = pd.to_datetime(stays["discharge"]).dt.date
    hits = []
    for stay in stays.itertuples(index=False):
        mask = (
            (lines.member_id == stay.member_id)
            & (lines.dos_from >= stay.admit)
            & (lines.dos_from <= stay.discharge)
            & (~lines.pos.isin(["21", "23"]))
        )
        hit = lines[mask]
        if hit.empty:
            continue
        hits.append(hit)
    if not hits:
        return []
    all_hit = pd.concat(hits, ignore_index=True).drop_duplicates("line_id")
    out: list[AlertDraft] = []
    for prov, grp in all_hit.groupby("billing_provider_id"):
        codes = set(grp["code"].astype(str))
        if len(grp) < 2 and "ABA-60" not in codes:
            continue
        out.append(
            AlertDraft(
                detector="rules",
                rule_id="R-IP-001",
                rule_version=1,
                entity_id=str(prov),
                entity_type="provider",
                line_ids=grp["line_id"].tolist()[:40],
                score=1.0,
                evidence={
                    "kind": "inpatient_overlap",
                    "n_lines": int(len(grp)),
                    "member_ids": sorted({str(m) for m in grp["member_id"].tolist()})[:8],
                },
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
    if evv is None or evv.empty:
        covered: set[tuple[Any, ...]] = set()
    else:
        evv = evv.copy()
        evv["day"] = pd.to_datetime(evv["start_ts"]).dt.date
        covered = set(
            zip(evv["member_id"].astype(str), evv["provider_id"].astype(str), evv["day"], strict=False)
        )
    lines["dos_from"] = pd.to_datetime(lines["dos_from"]).dt.date
    lines["member_id"] = lines["member_id"].astype(str)
    lines["billing_provider_id"] = lines["billing_provider_id"].astype(str)
    miss_mask = [
        (row.member_id, row.billing_provider_id, row.dos_from) not in covered
        for row in lines.itertuples(index=False)
    ]
    missed = lines[miss_mask]
    if missed.empty:
        return []
    totals = lines.groupby("billing_provider_id").size()
    out: list[AlertDraft] = []
    for prov, grp in missed.groupby("billing_provider_id"):
        n_miss = int(len(grp))
        n_total = int(totals.get(prov, n_miss))
        miss_rate = n_miss / max(1, n_total)
        out.append(
            AlertDraft(
                detector="rules",
                rule_id="R-EVV-001",
                rule_version=1,
                entity_id=str(prov),
                entity_type="provider",
                line_ids=grp["line_id"].tolist()[:40],
                score=round(min(1.0, 0.35 + 0.6 * miss_rate), 3),
                evidence={
                    "kind": "evv_missing",
                    "n_missing": n_miss,
                    "n_home_health": n_total,
                    "miss_rate": round(miss_rate, 3),
                    "member_ids": sorted({str(m) for m in grp["member_id"].tolist()})[:8],
                },
            )
        )
    return out


def _excluded(tables: dict[str, pd.DataFrame]) -> list[AlertDraft]:
    """Billing or rendering provider is on the exclusion list (NPI and name agree, DOS in window)."""
    excl = tables["exclusion_record"]
    if excl.empty or "npi" not in excl:
        return []
    by_npi = {str(r["npi"]): r for r in excl.to_dict("records") if r.get("npi") and pd.notna(r["npi"])}
    if not by_npi:
        return []
    providers = tables["provider"]
    claims = tables["claim"]
    lines = tables["claim_line"].merge(claims[["claim_id", "billing_provider_id"]], on="claim_id")
    out = []
    for prov in providers[providers.npi_syn.astype(str).isin(by_npi)].itertuples(index=False):
        record = by_npi[str(prov.npi_syn)]
        score = leie.name_score(prov.name, record)
        if score < leie.NAME_MATCH_MIN:
            # NPI collision with a different name: a data-quality lead, not an excluded party.
            continue
        party = lines.billing_provider_id == prov.provider_id
        if "rendering_provider_id" in lines:
            party |= lines.rendering_provider_id == prov.provider_id
        hit = lines[party & leie.exclusion_window_mask(lines["dos_from"], record)]
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
                evidence={
                    "kind": "excluded_party",
                    "npi": prov.npi_syn,
                    "excl_id": record.get("excl_id"),
                    "excl_date": leie.iso_date(record.get("excl_date")),
                    "match": "npi_and_name",
                    "name_score": round(score, 1),
                    "n_lines_after_exclusion": len(hit),
                },
            )
        )
    return out


RX_MIN_MME = 120
RX_MIN_PRESCRIBERS = 4
RX_MIN_PHARMACIES = 4
RX_WINDOW_DAYS = 180
RX_FILLS_SHOWN = 20


def _doctor_shopping(tables: dict[str, pd.DataFrame]) -> list[AlertDraft]:
    """Member-level opioid pattern: high-MME fills from 4+ prescribers and 4+ pharmacies in 180 days.

    The subject is the member (masked downstream), routed to pharmacy lock-in / care-coordination
    review. Prescribers and pharmacies are context, never the case subject, and the alert does not
    link into provider cases.
    """
    rx = tables.get("rx_fill")
    if rx is None or rx.empty:
        return []
    opioids = rx[(rx.drug_class_syn == "opioid") & (rx.mme >= RX_MIN_MME)].copy()
    if opioids.empty:
        return []
    opioids["fill_day"] = pd.to_datetime(opioids["fill_date"], errors="coerce")
    claims = tables["claim"][["claim_id", "member_id", "billing_provider_id"]]
    lines = tables["claim_line"].merge(claims, on="claim_id")
    rx_lines = lines[lines.code.astype(str).str.startswith("NDC-OPIOID")].copy()
    rx_lines["day"] = pd.to_datetime(rx_lines["dos_from"], errors="coerce")
    out = []
    for member_id, grp in opioids.sort_values("fill_day").groupby("member_id"):
        window = _rx_window(grp)
        if window is None:
            continue
        start, end = window["fill_day"].min(), window["fill_day"].max()
        prescribers = sorted(window["prescriber_id"].astype(str).unique())
        pharmacies = sorted(window["pharmacy_id"].astype(str).unique())
        hit = rx_lines[(rx_lines.member_id == member_id) & rx_lines.day.between(start, end)]
        fills = [
            {
                "fill_date": d.date().isoformat(),
                "prescriber_id": str(r.prescriber_id),
                "pharmacy_id": str(r.pharmacy_id),
                "mme": float(r.mme),
                "days_supply": int(r.days_supply),
            }
            for d, r in zip(window["fill_day"], window.itertuples(index=False), strict=True)
        ][:RX_FILLS_SHOWN]
        out.append(
            AlertDraft(
                detector="rules",
                rule_id="R-RX-001",
                rule_version=1,
                entity_id=str(member_id),
                entity_type="member",
                line_ids=hit["line_id"].tolist()[:40],
                score=0.85,
                related_entity_ids=prescribers + pharmacies,
                evidence={
                    "kind": "doctor_shopping",
                    "member_id": member_id,
                    "prescribers": len(prescribers),
                    "pharmacies": len(pharmacies),
                    "prescriber_ids": prescribers,
                    "pharmacy_ids": pharmacies,
                    "n_fills": int(len(window)),
                    "window_start": start.date().isoformat(),
                    "window_end": end.date().isoformat(),
                    "max_mme": float(window["mme"].max()),
                    "fills": fills,
                    "review_track": "pharmacy_lock_in",
                },
            )
        )
    return out


def _rx_window(fills: pd.DataFrame) -> pd.DataFrame | None:
    """First 180-day window with enough distinct prescribers and pharmacies, else None."""
    days = fills["fill_day"]
    for first in days.dropna().unique():
        window = fills[(days >= first) & (days < first + pd.Timedelta(days=RX_WINDOW_DAYS))]
        if window["prescriber_id"].nunique() >= RX_MIN_PRESCRIBERS and window["pharmacy_id"].nunique() >= RX_MIN_PHARMACIES:
            return window
    return None


SEX_CONFLICT_BYPASS_MODIFIERS = frozenset({"KX"})
SEX_CONFLICT_BYPASS_CONDITION_CODES = frozenset({"45"})


def _sex_implausible(tables: dict[str, pd.DataFrame]) -> list[AlertDraft]:
    """Sex-procedure coding conflict (data-quality check, not an FWA finding).

    Lines carrying the KX modifier, or claims with condition code 45, are excluded: CMS
    (Transmittal R1877CP) uses them to bypass gender/procedure edits for transgender and
    intersex patients.
    """
    members = tables["member"][["member_id", "sex"]]
    claim_cols = ["claim_id", "member_id", "billing_provider_id"]
    if "condition_codes" in tables["claim"]:
        claim_cols.append("condition_codes")
    lines = tables["claim_line"].merge(tables["claim"][claim_cols], on="claim_id")
    lines = lines.merge(members, on="member_id")
    hit = lines[(lines.code == "PROC-MALE-01") & (lines.sex == "F")]
    if not hit.empty:
        hit = hit[~hit["modifiers"].apply(lambda m: bool(set(_codes(m)) & SEX_CONFLICT_BYPASS_MODIFIERS))]
    if not hit.empty and "condition_codes" in hit:
        hit = hit[~hit["condition_codes"].apply(lambda c: bool(set(_codes(c)) & SEX_CONFLICT_BYPASS_CONDITION_CODES))]
    out: list[AlertDraft] = []
    for prov, grp in hit.groupby("billing_provider_id"):
        out.append(
            AlertDraft(
                detector="rules",
                rule_id="R-SEX-001",
                rule_version=1,
                entity_id=str(prov),
                entity_type="provider",
                line_ids=grp["line_id"].tolist()[:40],
                score=0.3,
                evidence={
                    "kind": "sex_implausible",
                    "n_lines": int(len(grp)),
                    "member_ids": sorted({str(m) for m in grp["member_id"].tolist()})[:8],
                    "bypass_checked": ["modifier KX", "condition code 45"],
                    "data_quality_check": True,
                },
            )
        )
    return out


def _codes(value: Any) -> list[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    if isinstance(value, str):
        return [v.strip().upper() for v in value.replace(";", ",").split(",") if v.strip()]
    return [str(v).strip().upper() for v in value]


def _pos_mismatch(tables: dict[str, pd.DataFrame]) -> list[AlertDraft]:
    lines = tables["claim_line"].merge(
        tables["claim"][["claim_id", "billing_provider_id"]], on="claim_id"
    )
    office_codes = {f"EM-EST-{i}" for i in range(1, 6)}
    hit = lines[lines.code.isin(office_codes) & lines.pos.isin(["21", "23", "41"])]
    out: list[AlertDraft] = []
    for prov, grp in hit.groupby("billing_provider_id"):
        out.append(
            AlertDraft(
                detector="rules",
                rule_id="R-POS-001",
                rule_version=1,
                entity_id=str(prov),
                entity_type="provider",
                line_ids=grp["line_id"].tolist()[:40],
                score=0.55,
                evidence={
                    "kind": "pos_mismatch",
                    "n_lines": int(len(grp)),
                    "pos_values": sorted({str(p) for p in grp["pos"].tolist()}),
                },
            )
        )
    return out


AMBULANCE_BASE_CODES = frozenset({"A0427", "A0429", "A0426", "A0428"})
AMBULANCE_MILEAGE_CODES = frozenset({"A0425"})
AMB_LONG_TRIP_MINUTES = 90
CLONE_MIN_MEMBERS = 8
CLONE_PEER_MULTIPLE = 3.0


def _ambulance_overlap(tables: dict[str, pd.DataFrame]) -> list[AlertDraft]:
    """Several long recorded trips for different members on one crew-day.

    A transport is billed as a base-rate line plus a mileage line, so lines for the same member,
    supplier and day are paired into one trip first; one transport never fires. The extract has
    no vehicle, crew or pickup times, so this cannot prove overlap: it surfaces crew-days whose
    recorded trip durations add up to more than one long run, for records review.
    """
    claims = tables["claim"][["claim_id", "member_id"]]
    lines = tables["claim_line"].merge(claims, on="claim_id")
    amb = lines[lines.code.isin(AMBULANCE_BASE_CODES | AMBULANCE_MILEAGE_CODES)]
    if amb.empty:
        return []
    trips = (
        amb.groupby(["rendering_provider_id", "dos_from", "member_id"], dropna=False)
        .agg(
            line_ids=("line_id", list),
            minutes=("minutes", "max"),
            has_base=("code", lambda c: bool(set(c) & AMBULANCE_BASE_CODES)),
        )
        .reset_index()
    )
    timed = trips[trips.minutes.fillna(0) > 0]
    out: list[AlertDraft] = []
    for (prov, dos), day in timed.groupby(["rendering_provider_id", "dos_from"], dropna=False):
        minutes = float(day["minutes"].sum())
        if day["member_id"].nunique() < 2 or minutes < 2 * AMB_LONG_TRIP_MINUTES:
            continue
        out.append(
            AlertDraft(
                detector="rules",
                rule_id="R-AMB-001",
                rule_version=1,
                entity_id=str(prov),
                entity_type="provider",
                line_ids=[lid for ids in day["line_ids"] for lid in ids],
                score=0.6,
                evidence={
                    "kind": "ambulance_overlap",
                    "trips": int(len(day)),
                    "minutes": minutes,
                    "dos": str(dos),
                    "trips_without_base_line": int((~day["has_base"]).sum()),
                    "member_ids": sorted({str(m) for m in day["member_id"]})[:8],
                    "overlap_tested": False,
                },
            )
        )
    return out


def _clone_billing(tables: dict[str, pd.DataFrame]) -> list[AlertDraft]:
    """Same service for many members on one provider-day, far above that code's peer volume.

    Fee-schedule payers pay the same amount for the same code, so identical paid amounts are
    expected and are not used. The signal is volume: distinct members per provider-day for the
    code against the 95th percentile of all provider-days billing that code (robust to the outlier itself).
    """
    claims = tables["claim"][["claim_id", "member_id", "billing_provider_id"]]
    lines = tables["claim_line"].merge(claims, on="claim_id")
    per_day = (
        lines.groupby(["billing_provider_id", "dos_from", "code"], dropna=False)
        .agg(members=("member_id", "nunique"), line_ids=("line_id", list))
        .reset_index()
    )
    peer_p95 = per_day.groupby("code")["members"].quantile(0.95)
    peer_median = per_day.groupby("code")["members"].median()
    out: list[AlertDraft] = []
    for row in per_day.itertuples(index=False):
        baseline = max(1.0, float(peer_p95.get(row.code, 1.0)))
        if row.members < CLONE_MIN_MEMBERS or row.members < CLONE_PEER_MULTIPLE * baseline:
            continue
        out.append(
            AlertDraft(
                detector="rules",
                rule_id="R-CLONE-001",
                rule_version=1,
                entity_id=str(row.billing_provider_id),
                entity_type="provider",
                line_ids=list(row.line_ids)[:40],
                score=0.7,
                evidence={
                    "kind": "clone_billing",
                    "members": int(row.members),
                    "code": str(row.code),
                    "dos": str(row.dos_from),
                    "peer_p95_members": round(baseline, 2),
                    "peer_median_members": float(peer_median.get(row.code, 1.0)),
                    "ratio_to_peer_p95": round(row.members / baseline, 1),
                },
            )
        )
    return out


def _stay_compression(tables: dict[str, pd.DataFrame]) -> list[AlertDraft]:
    stays = tables.get("inpatient_stay")
    claims = tables["claim"]
    if stays is None or stays.empty:
        same = claims[
            (claims.claim_type == "facility")
            & claims["admit"].notna()
            & claims["discharge"].notna()
        ].copy()
        if same.empty:
            return []
        same["admit"] = pd.to_datetime(same["admit"]).dt.date
        same["discharge"] = pd.to_datetime(same["discharge"]).dt.date
        same = same[same["admit"] == same["discharge"]]
    else:
        stays = stays.copy()
        stays["admit"] = pd.to_datetime(stays["admit"]).dt.date
        stays["discharge"] = pd.to_datetime(stays["discharge"]).dt.date
        same = stays[stays["admit"] == stays["discharge"]]
    if same.empty:
        return []
    lines = tables["claim_line"].merge(
        claims[["claim_id", "member_id", "billing_provider_id", "claim_type"]], on="claim_id"
    )
    lines["dos_from"] = pd.to_datetime(lines["dos_from"]).dt.date
    out: list[AlertDraft] = []
    for stay in same.itertuples(index=False):
        member_id = str(stay.member_id)
        day = stay.admit
        hit = lines[(lines.member_id.astype(str) == member_id) & (lines.dos_from == day)]
        high = hit[(hit.code == "FAC-DRG-HI") | (hit.paid >= 10_000) | (hit.claim_type == "facility")]
        if high.empty:
            continue
        out.append(
            AlertDraft(
                detector="rules",
                rule_id="R-STAY-001",
                rule_version=1,
                entity_id=str(high.iloc[0].billing_provider_id),
                entity_type="provider",
                line_ids=high["line_id"].tolist()[:20],
                score=0.9,
                evidence={
                    "kind": "stay_compression",
                    "member_id": member_id,
                    "admit": str(day),
                    "discharge": str(day),
                    "max_paid": float(high["paid"].max()),
                },
            )
        )
    return out


def _mileage_padding(tables: dict[str, pd.DataFrame]) -> list[AlertDraft]:
    providers = tables["provider"][["provider_id", "rural"]]
    lines = tables["claim_line"].merge(
        tables["claim"][["claim_id", "billing_provider_id"]], on="claim_id"
    )
    lines = lines.merge(providers, left_on="billing_provider_id", right_on="provider_id", how="left")
    hit = lines[(lines.code == "A0425") & (lines.units > 80) & (lines.rural != True)]  # noqa: E712
    if hit.empty:
        return []
    out: list[AlertDraft] = []
    for prov, grp in hit.groupby("billing_provider_id"):
        out.append(
            AlertDraft(
                detector="rules",
                rule_id="R-MILE-001",
                rule_version=1,
                entity_id=str(prov),
                entity_type="provider",
                line_ids=grp["line_id"].tolist()[:20],
                score=0.7,
                evidence={
                    "kind": "mileage_padding",
                    "n_lines": int(len(grp)),
                    "max_miles": float(grp["units"].max()),
                    "urban_cap": 80,
                },
            )
        )
    return out
