"""Exclusion-list (LEIE-style) matching.

An NPI hit alone is not an identity match: NPIs are mistyped and reused in source files, and
the OIG asks that a name hit be verified against a second identifier. A provider is treated as
the excluded party only when the NPI matches *and* the name agrees. Without an NPI (owners,
managing employees), name, date of birth and address must all agree. Claim lines count only
when the date of service falls inside the exclusion window.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any

import pandas as pd
from rapidfuzz import fuzz

NAME_MATCH_MIN = 90.0
_SUFFIXES = frozenset(
    {"md", "do", "np", "pa", "rn", "dds", "phd", "jr", "sr", "ii", "iii", "inc", "llc", "pc", "pllc", "corp", "co", "ltd"}
)
_DROPPED = re.compile(r"['.`]")  # O'Neil -> oneil, M.D. -> md
_NON_ALNUM = re.compile(r"[^a-z0-9 ]+")


def normalize_name(value: Any) -> str:
    """Lowercase, drop punctuation and credential/entity suffixes, collapse whitespace."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    words = _NON_ALNUM.sub(" ", _DROPPED.sub("", str(value).lower())).split()
    return " ".join(w for w in words if w not in _SUFFIXES)


def normalize_address(value: Any) -> str:
    text = normalize_name(value)
    for long, short in (("street", "st"), ("avenue", "ave"), ("suite", "ste"), ("road", "rd"), ("drive", "dr")):
        text = re.sub(rf"\b{long}\b", short, text)
    return text


def record_names(record: Any) -> list[str]:
    """Candidate names on an exclusion row: the person (first last) and the business name."""
    person = normalize_name(f"{_text(record, 'firstname')} {_text(record, 'lastname')}")
    business = normalize_name(_text(record, "busname"))
    return [name for name in (person, business) if name]


def name_score(name: Any, record: Any) -> float:
    target = normalize_name(name)
    if not target:
        return 0.0
    return max((fuzz.token_sort_ratio(target, candidate) for candidate in record_names(record)), default=0.0)


def names_agree(name: Any, record: Any) -> bool:
    return name_score(name, record) >= NAME_MATCH_MIN


def addresses_agree(left: Any, right: Any) -> bool:
    a, b = normalize_address(left), normalize_address(right)
    return bool(a and b) and fuzz.token_sort_ratio(a, b) >= NAME_MATCH_MIN


def exclusion_window_mask(dos: pd.Series, record: Any) -> pd.Series:
    """True for dates of service on or after the exclusion date and before any reinstatement."""
    when = pd.to_datetime(dos, errors="coerce")
    start = pd.to_datetime(_value(record, "excl_date"), errors="coerce")
    mask = when.notna()
    if pd.notna(start):
        mask &= when >= start
    end = pd.to_datetime(_value(record, "rein_date"), errors="coerce")
    if pd.notna(end):
        mask &= when < end
    return mask


def same_date(left: Any, right: Any) -> bool:
    a, b = pd.to_datetime(left, errors="coerce"), pd.to_datetime(right, errors="coerce")
    return bool(pd.notna(a) and pd.notna(b) and a.date() == b.date())


def iso_date(value: Any) -> str | None:
    stamp = pd.to_datetime(value, errors="coerce")
    if pd.isna(stamp):
        return None
    day: date = stamp.date()
    return day.isoformat()


def _value(record: Any, field: str) -> Any:
    return record.get(field) if isinstance(record, dict) else getattr(record, field, None)


def _text(record: Any, field: str) -> str:
    value = _value(record, field)
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value)
