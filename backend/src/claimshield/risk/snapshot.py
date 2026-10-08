"""Cut an extract back to what was knowable at a cutoff date.

Every risk feature is computed on ``as_of(tables, cutoff)``, never on the raw extract. This is
the guard for leakage trap 2 (late claims): a claim line counts only if its service date
*and* its claim's received date are on or before the cutoff. Investigation tables are dropped
entirely (trap 4, process features; and trap 6, because the generator samples investigation
subjects only from planted providers, so their presence is a label proxy).
"""

from __future__ import annotations

from datetime import date, datetime, time

import pandas as pd

PROCESS_TABLES = frozenset({"investigation", "investigation_subject"})


def _dates(frame: pd.DataFrame, column: str) -> pd.Series:
    return pd.to_datetime(frame[column], errors="coerce")


def _on_or_before(frame: pd.DataFrame, column: str, cutoff: pd.Timestamp) -> pd.Series:
    """True when the date is known and <= cutoff. Missing dates count as unknown, so excluded."""
    return _dates(frame, column) <= cutoff


def as_of(tables: dict[str, pd.DataFrame], cutoff: date) -> dict[str, pd.DataFrame]:
    ts = pd.Timestamp(cutoff)
    out: dict[str, pd.DataFrame] = {}
    for name, frame in tables.items():
        if name in PROCESS_TABLES:
            out[name] = frame.iloc[0:0].copy()
        else:
            out[name] = frame
    claims = tables["claim"]
    lines = tables["claim_line"]
    if "received_date" in claims.columns:
        claims = claims[_on_or_before(claims, "received_date", ts)]
    lines = lines[lines["claim_id"].isin(claims["claim_id"]) & _on_or_before(lines, "dos_from", ts)]
    out["claim"] = claims[claims["claim_id"].isin(lines["claim_id"])].copy()
    out["claim_line"] = lines.copy()

    providers = tables["provider"]
    if "enroll_date" in providers.columns:
        enrolled = _dates(providers, "enroll_date")
        providers = providers[enrolled.isna() | (enrolled <= ts)]
    out["provider"] = providers.copy()
    known = set(providers["provider_id"].astype(str))

    member = tables["member"].copy()
    if "date_of_death" in member.columns:
        death = _dates(member, "date_of_death")
        member["date_of_death"] = member["date_of_death"].where(death <= ts, None)
    out["member"] = member

    links = tables.get("ownership_link")
    if links is not None and not links.empty:
        keep = links["provider_id"].astype(str).isin(known)
        if "start" in links.columns:
            started = _dates(links, "start")
            keep &= started.isna() | (started <= ts)
        out["ownership_link"] = links[keep].copy()
    contacts = tables.get("contact_point")
    if contacts is not None and not contacts.empty:
        is_provider = contacts["entity_type"] == "provider"
        keep = ~is_provider | contacts["entity_id"].astype(str).isin(known)
        out["contact_point"] = contacts[keep].copy()

    for name, column in (
        ("referral", "date"),
        ("rx_fill", "fill_date"),
        ("exclusion_record", "excl_date"),
        ("eligibility_span", "start"),
    ):
        frame = tables.get(name)
        if frame is not None and not frame.empty and column in frame.columns:
            out[name] = frame[_on_or_before(frame, column, ts)].copy()
    stays = tables.get("inpatient_stay")
    if stays is not None and not stays.empty:
        # Only finished stays: an open stay's discharge date is not known yet.
        out["inpatient_stay"] = stays[_on_or_before(stays, "discharge", ts)].copy()
    evv = tables.get("evv_visit")
    if evv is not None and not evv.empty:
        end_of_day = pd.Timestamp(datetime.combine(cutoff, time.max), tz="UTC")
        started = pd.to_datetime(evv["start_ts"], errors="coerce", utc=True)
        out["evv_visit"] = evv[started <= end_of_day].copy()
    return out


def data_cutoff(tables: dict[str, pd.DataFrame]) -> date:
    """The as-of date used to score an extract: its latest service date.

    Training cutoffs see a window whose last weeks are only partly received. Scoring at the
    latest service date (and dropping claims received after it) gives the live extract the
    same shape. Scoring at the latest received date instead would show weeks with no service
    at all and read as every provider going quiet.
    """
    latest = _dates(tables["claim_line"], "dos_from").max()
    if pd.isna(latest):
        return date.today()
    return date(latest.year, latest.month, latest.day)
