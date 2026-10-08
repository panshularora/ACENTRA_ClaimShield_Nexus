from __future__ import annotations

import contextlib
from collections.abc import Sequence
from datetime import date, datetime
from typing import Any

import pandas as pd
from sqlalchemy import inspect as sa_inspect
from sqlalchemy import select
from sqlalchemy.orm import Mapper, Session

from claimshield.core.ids import new_id
from claimshield.db import models
from claimshield.synth.generator import Dataset

TABLE_MODELS: dict[str, type] = {
    "member": models.Member,
    "eligibility_span": models.EligibilitySpan,
    "location": models.Location,
    "provider": models.Provider,
    "facility": models.Facility,
    "owner": models.Owner,
    "ownership_link": models.OwnershipLink,
    "contact_point": models.ContactPoint,
    "referral": models.Referral,
    "claim": models.Claim,
    "claim_line": models.ClaimLine,
    "inpatient_stay": models.InpatientStay,
    "evv_visit": models.EvvVisit,
    "rx_fill": models.RxFill,
    "exclusion_record": models.ExclusionRecord,
    "investigation": models.Investigation,
    "investigation_subject": models.InvestigationSubject,
}


def load_tables(session: Session) -> dict[str, pd.DataFrame]:
    """Rebuild detector tables from persisted rows so a run can re-lane without regenerating."""
    tables: dict[str, pd.DataFrame] = {}
    for name, model in TABLE_MODELS.items():
        mapper: Mapper[Any] = sa_inspect(model)
        cols = [col.key for col in mapper.columns if col.key != "id"]
        rows: Sequence[Any] = session.execute(select(model)).scalars().all()
        records = [{col: getattr(obj, col) for col in cols} for obj in rows]
        tables[name] = pd.DataFrame.from_records(records, columns=cols)
    return tables


def persist_dataset(session: Session, dataset: Dataset) -> dict[str, Any]:
    report: dict[str, Any] = {"tables": []}
    for name, model in TABLE_MODELS.items():
        frame = dataset.tables.get(name)
        if frame is None or frame.empty:
            report["tables"].append({"name": name, "loaded": 0, "skipped": 0, "rejected": 0})
            continue
        records = frame.to_dict(orient="records")
        cleaned = [_clean_record(rec) for rec in records]
        to_insert = _new_rows(session, model, cleaned)
        if to_insert:
            session.bulk_insert_mappings(model, to_insert)
        report["tables"].append(
            {
                "name": name,
                "loaded": len(to_insert),
                "skipped": len(cleaned) - len(to_insert),
                "rejected": 0,
            }
        )
    report["ground_truth_rows"] = len(dataset.ground_truth)
    report["data_card"] = dataset.data_card
    report["batch_tag"] = new_id("BAT")
    report["scheme_ids"] = sorted(
        {str(s) for s in dataset.ground_truth.get("scheme_id", pd.Series(dtype=str)).dropna().unique()}
    )
    return report


def _new_rows(session: Session, model: type, cleaned: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Skip rows that already exist so a second load of the same seed is idempotent."""
    mapper: Mapper[Any] = sa_inspect(model)
    pk_cols = [str(col.key) for col in mapper.primary_key]
    if len(pk_cols) == 1 and pk_cols[0] != "id":
        pk = pk_cols[0]
        existing = set(session.execute(select(getattr(model, pk))).scalars().all())
        return [row for row in cleaned if row.get(pk) not in existing]
    natural_cols = [col.key for col in mapper.columns if col.key != "id"]
    existing = {
        tuple(_fingerprint(value) for value in db_row)
        for db_row in session.execute(select(*(getattr(model, col) for col in natural_cols))).all()
    }
    fresh: list[dict[str, Any]] = []
    for row in cleaned:
        key = tuple(_fingerprint(row.get(col)) for col in natural_cols)
        if key in existing:
            continue
        existing.add(key)
        fresh.append(row)
    return fresh


def _fingerprint(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, list):
        return tuple(_fingerprint(item) for item in value)
    if isinstance(value, dict):
        return tuple(sorted((k, _fingerprint(v)) for k, v in value.items()))
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


def _clean_record(rec: dict[str, Any]) -> dict[str, Any]:
    rec = dict(rec)
    rec.pop("id", None)
    out: dict[str, Any] = {}
    for key, value in rec.items():
        if value is None:
            out[key] = None
            continue
        if isinstance(value, (list, dict)):
            out[key] = value
            continue
        try:
            if pd.isna(value):
                out[key] = None
                continue
        except (TypeError, ValueError):
            pass
        if hasattr(value, "item") and not isinstance(value, (bytes, str, datetime, date)):
            with contextlib.suppress(ValueError, AttributeError):
                value = value.item()
        if isinstance(value, pd.Timestamp):
            if value.tzinfo is not None or value.hour or value.minute or value.second:
                out[key] = value.to_pydatetime()
            else:
                out[key] = value.date()
            continue
        out[key] = value
    return out
