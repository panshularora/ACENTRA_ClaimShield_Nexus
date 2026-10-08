"""Load a ClaimShield extract directory of CSVs into a Dataset.

The generator writes one CSV per table (see synth.export). S3 ingest reuses that layout.
"""

from __future__ import annotations

import ast
import json
import re
from io import BytesIO
from typing import Any

import pandas as pd

from claimshield.core.errors import ValidationFailed
from claimshield.ingest.service import TABLE_MODELS
from claimshield.synth.generator import Dataset

TABLE_ALIASES: dict[str, str] = {
    "claims": "claim",
    "claim_lines": "claim_line",
    "members": "member",
    "providers": "provider",
    "locations": "location",
    "facilities": "facility",
    "owners": "owner",
    "ownership_links": "ownership_link",
    "contact_points": "contact_point",
    "referrals": "referral",
    "evv": "evv_visit",
    "evv_visits": "evv_visit",
    "rx": "rx_fill",
    "rx_fills": "rx_fill",
    "eligibility": "eligibility_span",
    "eligibility_spans": "eligibility_span",
    "inpatient_stays": "inpatient_stay",
    "exclusion_records": "exclusion_record",
    "investigations": "investigation",
    "investigation_subjects": "investigation_subject",
}

REQUIRED_TABLES: tuple[str, ...] = ("member", "provider", "claim", "claim_line")

REQUIRED_COLUMNS: dict[str, frozenset[str]] = {
    "claim": frozenset({"claim_id", "member_id", "billing_provider_id", "received_date", "adjudicated_date"}),
    "claim_line": frozenset(
        {
            "line_id",
            "claim_id",
            "rendering_provider_id",
            "dos_from",
            "dos_to",
            "code",
            "charge",
            "allowed",
            "paid",
        }
    ),
    "member": frozenset({"member_id", "name", "dob", "sex", "location_id"}),
    "provider": frozenset({"provider_id", "name", "kind", "specialty", "service_line", "location_id"}),
}

SKIP_FILES = frozenset({"ground_truth", "data_card", "readme"})

DATE_COLUMNS = frozenset(
    {
        "dob",
        "date_of_death",
        "enroll_date",
        "term_date",
        "received_date",
        "adjudicated_date",
        "admit",
        "discharge",
        "dos_from",
        "dos_to",
        "start",
        "end",
        "fill_date",
        "date",
        "sla_due",
        "excl_date",
        "rein_date",
        "opened",
        "closed",
    }
)
DATETIME_COLUMNS = frozenset({"start_ts", "end_ts", "created_at", "updated_at"})
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def table_name_from_key(key: str) -> str | None:
    filename = key.rsplit("/", 1)[-1]
    if not filename.lower().endswith(".csv"):
        return None
    stem = filename[:-4]
    lowered = stem.lower()
    if lowered in SKIP_FILES:
        return None
    if lowered in TABLE_MODELS:
        return lowered
    return TABLE_ALIASES.get(lowered)


def extract_prefix(key: str) -> str:
    if "/" not in key:
        return ""
    return key.rsplit("/", 1)[0] + "/"


def parse_csv_bytes(raw: bytes, *, table: str, max_bytes: int) -> pd.DataFrame:
    if len(raw) > max_bytes:
        raise ValidationFailed("csv exceeds size limit")
    if not raw.strip():
        raise ValidationFailed(f"{table} csv is empty")
    try:
        frame = pd.read_csv(BytesIO(raw))
    except Exception as exc:
        raise ValidationFailed(f"{table} csv is not readable") from exc
    if frame.empty and table in REQUIRED_TABLES:
        raise ValidationFailed(f"{table} csv has no rows")
    frame.columns = [str(col).strip() for col in frame.columns]
    needed = REQUIRED_COLUMNS.get(table)
    if needed:
        missing = sorted(needed - set(frame.columns))
        if missing:
            raise ValidationFailed(f"{table} csv missing columns")
    return _parse_cells(_coerce_types(frame))


def dataset_from_tables(
    tables: dict[str, pd.DataFrame],
    *,
    source: str,
) -> Dataset:
    missing = [name for name in REQUIRED_TABLES if name not in tables or tables[name].empty]
    if missing:
        raise ValidationFailed("extract is missing required tables")
    filled: dict[str, pd.DataFrame] = {}
    for name in TABLE_MODELS:
        if name in tables:
            filled[name] = tables[name]
        else:
            filled[name] = pd.DataFrame()
    n_lines = len(filled["claim_line"])
    n_claims = len(filled["claim"])
    ds = Dataset(profile="s3", seed=0, tables=filled)
    ds.data_card = {
        "source": source,
        "n_members": len(filled["member"]),
        "n_providers": len(filled["provider"]),
        "n_claims": n_claims,
        "n_claim_lines": n_lines,
        "limitations": ["external extract", "labels partial"],
    }
    return ds


def _coerce_types(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    for col in out.columns:
        if col in DATETIME_COLUMNS:
            out[col] = pd.to_datetime(out[col], errors="coerce", utc=True)
            continue
        if col in DATE_COLUMNS or _column_is_iso_date(out[col]):
            parsed = pd.to_datetime(out[col], errors="coerce")
            out[col] = parsed.dt.date
    return out


def _column_is_iso_date(series: pd.Series) -> bool:
    sample = series.dropna().astype(str).head(12)
    if sample.empty:
        return False
    return bool(sample.str.match(_ISO_DATE.pattern).all())


def _parse_cells(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    for col in out.columns:
        out[col] = out[col].map(_parse_cell)
    return out


def _parse_cell(value: Any) -> Any:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if not isinstance(value, str):
        return value
    text = value.strip()
    if not text:
        return None
    if text[:1] in "[{":
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            try:
                parsed = ast.literal_eval(text)
            except (SyntaxError, ValueError):
                return value
            return parsed
    return value
