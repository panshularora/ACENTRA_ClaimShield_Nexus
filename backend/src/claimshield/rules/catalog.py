from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

_DEFAULT = Path(__file__).resolve().parents[4] / "data" / "reference" / "rules.yaml"


def _scalar(raw: str) -> str | int | float:
    text = raw.strip()
    if text.isdigit() or (text.startswith("-") and text[1:].isdigit()):
        return int(text)
    try:
        return float(text)
    except ValueError:
        return text


def _parse_rules_yaml(text: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in text.splitlines():
        if line.startswith("  - "):
            if current:
                items.append(current)
            current = {}
            rest = line[4:]
            if ":" in rest:
                key, value = rest.split(":", 1)
                current[key.strip()] = _scalar(value)
        elif current is not None and line.startswith("    ") and ":" in line:
            key, value = line.strip().split(":", 1)
            current[key] = _scalar(value)
    if current:
        items.append(current)
    return items


@lru_cache
def load_rule_catalog(path: str | None = None) -> dict[str, dict[str, Any]]:
    target = Path(path) if path else _DEFAULT
    if not target.exists():
        return {}
    items = _parse_rules_yaml(target.read_text())
    return {str(item["rule_id"]): item for item in items if "rule_id" in item}


def rule_title(rule_id: str | None, fallback: str | None = None) -> str | None:
    if not rule_id:
        return fallback
    spec = load_rule_catalog().get(rule_id)
    if spec and spec.get("title"):
        return str(spec["title"])
    return fallback or rule_id


def stamp_catalog(alerts: list[Any]) -> list[Any]:
    catalog = load_rule_catalog()
    for alert in alerts:
        spec = catalog.get(getattr(alert, "rule_id", None))
        if not spec:
            continue
        evidence = getattr(alert, "evidence", None)
        if not isinstance(evidence, dict):
            continue
        evidence.setdefault("policy_ref", spec.get("policy_ref"))
        evidence.setdefault("rule_title", spec.get("title"))
        evidence.setdefault("severity", spec.get("severity"))
        evidence.setdefault("kind", spec.get("kind") or evidence.get("kind"))
    return alerts
