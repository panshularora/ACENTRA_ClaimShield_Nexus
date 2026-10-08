from __future__ import annotations

from datetime import date, datetime
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

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


def persist_dataset(session: Session, dataset: Dataset) -> dict[str, Any]:
    report: dict[str, Any] = {"tables": []}
    for name, model in TABLE_MODELS.items():
        frame = dataset.tables.get(name)
        if frame is None or frame.empty:
            report["tables"].append({"name": name, "loaded": 0, "rejected": 0})
            continue
        records = frame.to_dict(orient="records")
        cleaned = [_clean_record(rec) for rec in records]
        session.bulk_insert_mappings(model, cleaned)
        report["tables"].append({"name": name, "loaded": len(cleaned), "rejected": 0})
    report["ground_truth_rows"] = int(len(dataset.ground_truth))
    report["data_card"] = dataset.data_card
    report["batch_tag"] = new_id("BAT")
    report["scheme_ids"] = sorted(
        {str(s) for s in dataset.ground_truth.get("scheme_id", pd.Series(dtype=str)).dropna().unique()}
    )
    return report


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
            try:
                value = value.item()
            except (ValueError, AttributeError):
                pass
        if isinstance(value, pd.Timestamp):
            if value.tzinfo is not None or value.hour or value.minute or value.second:
                out[key] = value.to_pydatetime()
            else:
                out[key] = value.date()
            continue
        out[key] = value
    return out
