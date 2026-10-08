from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd
from faker import Faker

from claimshield.synth.codes import (
    ABA_HOUR,
    AMB_ALS,
    AMB_MILEAGE,
    BH_TIMED,
    CODE_SYSTEM_HCPCS2,
    CODE_SYSTEM_NDC,
    CODE_SYSTEM_SYNTH,
    DME_CATH,
    EM_LEVELS,
    HOME_VISIT,
    LAB_GENETIC,
    LAB_PANEL,
    POS_AMBULANCE,
    POS_HOME,
    POS_INPATIENT,
    POS_OFFICE,
    SERVICE_LINES,
    SPECIALTIES,
)
from claimshield.synth.luhn import random_npi
from claimshield.synth.profiles import PROFILES, Profile
from claimshield.synth.schemes import plant_all_schemes

ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _rid(rng: np.random.Generator, prefix: str, n: int = 10) -> str:
    chars = "".join(ALPHABET[int(rng.integers(0, len(ALPHABET)))] for _ in range(n))
    return f"{prefix}-{chars}"


def _jitter_money(rng: np.random.Generator, base: float) -> float:
    noise = float(rng.normal(0, 0.07))
    value = max(8.0, base * (1.0 + noise))
    return round(value, 2)


def _add_days(start: date, days: int) -> date:
    return start + timedelta(days=int(days))


@dataclass
class Dataset:
    profile: str
    seed: int
    tables: dict[str, pd.DataFrame] = field(default_factory=dict)
    ground_truth: pd.DataFrame = field(default_factory=pd.DataFrame)
    data_card: dict[str, Any] = field(default_factory=dict)

    def table(self, name: str) -> pd.DataFrame:
        return self.tables[name]


def generate(profile: str = "tiny", seed: int = 7) -> Dataset:
    if profile not in PROFILES:
        raise ValueError(f"unknown profile {profile}")
    spec = PROFILES[profile]
    rng = np.random.default_rng(seed)
    fake = Faker()
    fake.seed_instance(seed)

    start = date(2024, 1, 1)
    end = _add_days(start, spec.n_months * 30)

    locations = _locations(rng, fake, spec)
    members = _members(rng, fake, spec, locations, start, end)
    providers = _providers(rng, fake, spec, locations, start)
    owners, ownership, contacts = _ownership(rng, fake, spec, providers, start)
    facilities = _facilities(rng, locations)
    claims, lines, stays = _legitimate_claims(
        rng, spec, members, providers, facilities, start, end
    )
    referrals = _referrals(rng, spec, members, providers, start, end)
    evv = pd.DataFrame(
        columns=[
            "visit_id",
            "aide_id",
            "member_id",
            "provider_id",
            "start_ts",
            "end_ts",
            "lat",
            "lon",
            "service_type",
        ]
    )
    rx = _rx(rng, spec, members, providers, start, end)
    exclusions = _exclusions(rng, fake, providers, start)

    ds = Dataset(profile=profile, seed=seed)
    ds.tables = {
        "location": locations,
        "member": members,
        "provider": providers,
        "owner": owners,
        "ownership_link": ownership,
        "contact_point": contacts,
        "facility": facilities,
        "claim": claims,
        "claim_line": lines,
        "inpatient_stay": stays,
        "referral": referrals,
        "evv_visit": evv,
        "rx_fill": rx,
        "exclusion_record": exclusions,
        "eligibility_span": _eligibility(members, start, end),
    }
    plant_all_schemes(ds, rng, fake, start, end, spec)
    skip_evv: set[str] = set()
    if not ds.ground_truth.empty:
        for _, row in ds.ground_truth[ds.ground_truth["scheme_id"] == "S09"].iterrows():
            ids = row.line_ids
            if isinstance(ids, list):
                skip_evv.update(str(x) for x in ids)
    _attach_home_health_evv(ds, rng, skip_line_ids=skip_evv)
    _investigations(ds, rng, start, end, spec)
    ds.data_card = {
        "profile": profile,
        "seed": seed,
        "n_members": len(ds.tables["member"]),
        "n_providers": len(ds.tables["provider"]),
        "n_claim_lines": len(ds.tables["claim_line"]),
        "n_schemes": len(ds.ground_truth),
        "code_systems": sorted(ds.tables["claim_line"]["code_system"].unique().tolist()),
        "base_rates": "design knobs, not prevalence estimates",
        "limitations": [
            "synthetic data",
            "no medical records",
            "labels partial and noisy",
        ],
    }
    return ds


def _locations(rng: np.random.Generator, fake: Faker, spec: Profile) -> pd.DataFrame:
    types = [
        "clinic",
        "hospital",
        "dme",
        "lab",
        "pharmacy",
        "ambulance_base",
        "residence",
    ]
    rows = []
    for i in range(spec.n_locations):
        loc_type = "hospital" if i == 0 else str(rng.choice(types))
        rows.append(
            {
                "location_id": _rid(rng, "LOC"),
                "address_norm": fake.street_address().upper(),
                "zip": fake.zipcode()[:5],
                "lat": float(rng.uniform(33.5, 42.5)),
                "lon": float(rng.uniform(-88.0, -71.0)),
                "type": loc_type,
                "capacity": int(rng.integers(8, 80)) if loc_type in {"clinic", "hospital"} else None,
            }
        )
    return pd.DataFrame(rows)


def _members(
    rng: np.random.Generator,
    fake: Faker,
    spec: Profile,
    locations: pd.DataFrame,
    start: date,
    end: date,
) -> pd.DataFrame:
    loc_ids = locations["location_id"].tolist()
    rows = []
    family_addr = {i: loc_ids[int(rng.integers(0, len(loc_ids)))] for i in range(max(4, spec.n_members // 25))}
    for i in range(spec.n_members):
        sex = str(rng.choice(["F", "M"], p=[0.52, 0.48]))
        age = int(rng.choice([6, 14, 28, 45, 67, 78], p=[0.08, 0.07, 0.25, 0.28, 0.2, 0.12]))
        dob = date(start.year - age, int(rng.integers(1, 13)), int(rng.integers(1, 28)))
        died = rng.random() < 0.015 or i < 2
        dod = _add_days(start, int(rng.integers(40, (end - start).days - 10))) if died else None
        loc = family_addr[i % len(family_addr)] if rng.random() < 0.12 else loc_ids[int(rng.integers(0, len(loc_ids)))]
        rows.append(
            {
                "member_id": _rid(rng, "MBR"),
                "name": fake.name(),
                "dob": dob,
                "sex": sex,
                "county": fake.city(),
                "location_id": loc,
                "risk_tier": int(rng.integers(1, 5)),
                "date_of_death": dod,
            }
        )
    return pd.DataFrame(rows)


def _providers(
    rng: np.random.Generator,
    fake: Faker,
    spec: Profile,
    locations: pd.DataFrame,
    start: date,
) -> pd.DataFrame:
    loc_ids = locations["location_id"].tolist()
    rows = []
    for i in range(spec.n_providers):
        line = SERVICE_LINES[i % len(SERVICE_LINES)]
        specialty = str(rng.choice(SPECIALTIES[line]))
        rural = bool(rng.random() < 0.18)
        rows.append(
            {
                "provider_id": _rid(rng, "PRV"),
                "npi_syn": random_npi(rng),
                "name": fake.company() if rng.random() < 0.4 else fake.name(),
                "kind": "organization" if rng.random() < 0.45 else "individual",
                "specialty": specialty,
                "service_line": line,
                "location_id": loc_ids[int(rng.integers(0, len(loc_ids)))],
                "enroll_date": _add_days(start, -int(rng.integers(30, 800))),
                "term_date": None,
                "tin_token": _rid(rng, "TIN", 8),
                "rural": rural,
                "sole_community": rural and rng.random() < 0.25,
            }
        )
    return pd.DataFrame(rows)


def _ownership(
    rng: np.random.Generator,
    fake: Faker,
    spec: Profile,
    providers: pd.DataFrame,
    start: date,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    owners = []
    links = []
    contacts = []
    for _ in range(spec.n_owners):
        oid = _rid(rng, "OWN")
        kind = "person" if rng.random() < 0.7 else "org"
        owners.append(
            {
                "owner_id": oid,
                "kind": kind,
                "name": fake.name() if kind == "person" else fake.company(),
                "dob": date(1960 + int(rng.integers(0, 30)), 6, 15) if kind == "person" else None,
            }
        )
        phone = _rid(rng, "PH", 8)
        bank = _rid(rng, "BK", 8)
        contacts.append({"entity_id": oid, "entity_type": "owner", "kind": "phone", "value_hash": phone})
        contacts.append({"entity_id": oid, "entity_type": "owner", "kind": "bank_token", "value_hash": bank})
    owner_ids = [str(o["owner_id"]) for o in owners]
    for _, prov in providers.iterrows():
        oid = owner_ids[int(rng.integers(0, len(owner_ids)))]
        links.append(
            {
                "owner_id": oid,
                "provider_id": prov.provider_id,
                "pct": float(rng.choice([100.0, 60.0, 40.0, 25.0])),
                "start": prov.enroll_date,
                "end": None,
            }
        )
        contacts.append(
            {
                "entity_id": prov.provider_id,
                "entity_type": "provider",
                "kind": "phone",
                "value_hash": _rid(rng, "PH", 8),
            }
        )
    return pd.DataFrame(owners), pd.DataFrame(links), pd.DataFrame(contacts)


def _facilities(rng: np.random.Generator, locations: pd.DataFrame) -> pd.DataFrame:
    hospitals = locations[locations["type"] == "hospital"]
    if hospitals.empty:
        hospitals = locations.head(3)
    rows = []
    for _, loc in hospitals.iterrows():
        rows.append(
            {
                "facility_id": _rid(rng, "FAC"),
                "location_id": loc.location_id,
                "type": "hospital",
                "capacity": loc.capacity or 40,
            }
        )
    return pd.DataFrame(rows)


def _eligibility(members: pd.DataFrame, start: date, end: date) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "member_id": m.member_id,
                "start": start,
                "end": m.date_of_death or end,
                "program": "FFS" if i % 3 else "MCO",
            }
            for i, m in members.iterrows()
        ]
    )


def _pick_code(rng: np.random.Generator, line: str) -> tuple[str, str, str, int | None, float | None]:
    if line == "professional":
        code = str(rng.choice(EM_LEVELS, p=[0.08, 0.22, 0.4, 0.22, 0.08]))
        return CODE_SYSTEM_SYNTH, code, POS_OFFICE, None, None
    if line == "behavioral_health":
        code = str(rng.choice([*BH_TIMED, ABA_HOUR]))
        minutes = {"PSY-30": 30, "PSY-45": 45, "PSY-60": 60, ABA_HOUR: 60}[code]
        return CODE_SYSTEM_SYNTH, code, POS_OFFICE, minutes, None
    if line == "laboratory":
        code = str(rng.choice([LAB_PANEL, LAB_GENETIC]))
        return CODE_SYSTEM_SYNTH, code, POS_OFFICE, None, None
    if line == "home_health":
        return CODE_SYSTEM_SYNTH, HOME_VISIT, POS_HOME, 45, None
    if line == "ambulance":
        if rng.random() < 0.5:
            return CODE_SYSTEM_HCPCS2, AMB_MILEAGE, POS_AMBULANCE, None, float(rng.integers(4, 40))
        return CODE_SYSTEM_HCPCS2, AMB_ALS, POS_AMBULANCE, None, None
    if line == "dme":
        return CODE_SYSTEM_SYNTH, DME_CATH, POS_HOME, None, None
    if line == "pharmacy":
        return CODE_SYSTEM_NDC, "NDC-OPIOID-01", POS_OFFICE, None, None
    return CODE_SYSTEM_SYNTH, "FAC-DAY", POS_INPATIENT, None, None


def _legitimate_claims(
    rng: np.random.Generator,
    spec: Profile,
    members: pd.DataFrame,
    providers: pd.DataFrame,
    facilities: pd.DataFrame,
    start: date,
    end: date,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    span = max(1, (end - start).days)
    n = spec.target_lines
    claims = []
    lines = []
    stays = []
    member_ids = members["member_id"].tolist()
    living_ids = members.loc[members["date_of_death"].isna(), "member_id"].astype(str).tolist()
    if not living_ids:
        living_ids = [str(m) for m in member_ids]
    prov_by_line = {
        line: providers[providers.service_line == line]["provider_id"].tolist()
        for line in SERVICE_LINES
    }
    fac_ids = facilities["facility_id"].tolist() or [None]
    for _ in range(n):
        line_type = str(rng.choice(SERVICE_LINES, p=[0.28, 0.1, 0.08, 0.08, 0.08, 0.14, 0.16, 0.08]))
        pool = prov_by_line.get(line_type) or providers["provider_id"].tolist()
        provider_id = str(rng.choice(pool))
        dos = _add_days(start, int(rng.integers(0, span)))
        member_id = str(rng.choice(living_ids))
        lag = int(rng.integers(0, 45))
        received = _add_days(dos, lag)
        claim_id = _rid(rng, "CLM")
        line_id = _rid(rng, "LN")
        code_system, code, pos, minutes, mileage = _pick_code(rng, line_type)
        units = 1.0 if mileage is None else mileage
        charge = _jitter_money(rng, 180 if line_type != "ambulance" else 9 * units)
        allowed = round(charge * 0.82, 2)
        paid = round(allowed * 0.9, 2)
        facility_id = str(rng.choice(fac_ids)) if line_type == "facility" else None
        claims.append(
            {
                "claim_id": claim_id,
                "claim_type": line_type,
                "member_id": member_id,
                "billing_provider_id": provider_id,
                "facility_id": facility_id,
                "admit": dos if line_type == "facility" else None,
                "discharge": _add_days(dos, int(rng.integers(1, 5))) if line_type == "facility" else None,
                "received_date": received,
                "adjudicated_date": _add_days(received, int(rng.integers(1, 14))),
                "status": "paid",
                "source_system": "generator",
                "source_ref": None,
            }
        )
        lines.append(
            {
                "line_id": line_id,
                "claim_id": claim_id,
                "rendering_provider_id": provider_id,
                "ordering_provider_id": provider_id,
                "dos_from": dos,
                "dos_to": dos,
                "code_system": code_system,
                "code": code,
                "modifiers": [],
                "units": units,
                "minutes": minutes,
                "mileage": mileage,
                "dx": ["SYN-DX-01"],
                "pos": pos,
                "charge": charge,
                "allowed": allowed,
                "paid": paid,
            }
        )
        if line_type == "facility" and rng.random() < 0.4:
            stays.append(
                {
                    "member_id": member_id,
                    "facility_id": facility_id,
                    "admit": dos,
                    "discharge": _add_days(dos, int(rng.integers(2, 8))),
                }
            )
    if not stays:
        member_id = str(rng.choice(member_ids))
        dos = _add_days(start, 40)
        facility_id = str(fac_ids[0]) if fac_ids[0] is not None else None
        stays.append(
            {
                "member_id": member_id,
                "facility_id": facility_id,
                "admit": dos,
                "discharge": _add_days(dos, 4),
            }
        )
    return pd.DataFrame(claims), pd.DataFrame(lines), pd.DataFrame(stays)


def _referrals(
    rng: np.random.Generator,
    spec: Profile,
    members: pd.DataFrame,
    providers: pd.DataFrame,
    start: date,
    end: date,
) -> pd.DataFrame:
    span = max(1, (end - start).days)
    pids = providers["provider_id"].tolist()
    mids = members["member_id"].tolist()
    rows = []
    for _ in range(spec.n_referrals):
        a, b = rng.choice(pids, size=2, replace=False)
        rows.append(
            {
                "referring_id": str(a),
                "receiving_id": str(b),
                "member_id": str(rng.choice(mids)),
                "date": _add_days(start, int(rng.integers(0, span))),
                "kind": str(rng.choice(["referral", "order", "prescription"])),
            }
        )
    return pd.DataFrame(rows)


def _attach_home_health_evv(
    ds: Dataset, rng: np.random.Generator, *, skip_line_ids: set[str]
) -> None:
    """Write an EVV row for every home-health claim line except planted S09 misses."""
    claims = ds.tables["claim"]
    hh = claims[claims.claim_type == "home_health"]
    if hh.empty:
        return
    lines = ds.tables["claim_line"].merge(
        hh[["claim_id", "member_id", "billing_provider_id"]], on="claim_id"
    )
    members = ds.tables["member"].set_index("member_id")
    locations = ds.tables["location"].set_index("location_id")
    rows: list[dict[str, Any]] = []
    for row in lines.itertuples(index=False):
        if str(row.line_id) in skip_line_ids:
            continue
        member = members.loc[row.member_id]
        loc = locations.loc[member.location_id]
        dos = pd.Timestamp(row.dos_from).date()
        hour = int(rng.integers(7, 18))
        start_ts = datetime(dos.year, dos.month, dos.day, hour, int(rng.integers(0, 50)), tzinfo=UTC)
        minutes = int(row.minutes) if pd.notna(row.minutes) and row.minutes else 45
        rows.append(
            {
                "visit_id": _rid(rng, "EVV"),
                "aide_id": _rid(rng, "AID", 6),
                "member_id": row.member_id,
                "provider_id": str(row.billing_provider_id),
                "start_ts": start_ts,
                "end_ts": start_ts + timedelta(minutes=minutes),
                "lat": float(loc.lat),
                "lon": float(loc.lon),
                "service_type": "personal_care",
            }
        )
    extra = pd.DataFrame(rows)
    if extra.empty:
        return
    existing = ds.tables["evv_visit"]
    ds.tables["evv_visit"] = pd.concat([existing, extra], ignore_index=True)


def _rx(
    rng: np.random.Generator,
    spec: Profile,
    members: pd.DataFrame,
    providers: pd.DataFrame,
    start: date,
    end: date,
) -> pd.DataFrame:
    prescribers = providers[providers.service_line == "professional"]["provider_id"].tolist() or providers[
        "provider_id"
    ].tolist()
    pharmacies = providers[providers.service_line == "pharmacy"]["provider_id"].tolist() or providers[
        "provider_id"
    ].tolist()
    span = max(1, (end - start).days)
    rows = []
    for _ in range(spec.n_rx):
        rows.append(
            {
                "member_id": str(rng.choice(members["member_id"].tolist())),
                "prescriber_id": str(rng.choice(prescribers)),
                "pharmacy_id": str(rng.choice(pharmacies)),
                "drug_class_syn": str(rng.choice(["opioid", "statin", "insulin", "antibiotic"])),
                "days_supply": int(rng.choice([7, 14, 30])),
                "qty": float(rng.choice([15, 30, 60, 90])),
                "mme": float(rng.choice([0, 20, 40, 80])),
                "fill_date": _add_days(start, int(rng.integers(0, span))),
            }
        )
    return pd.DataFrame(rows)


def _exclusions(
    rng: np.random.Generator, fake: Faker, providers: pd.DataFrame, start: date
) -> pd.DataFrame:
    rows = []
    for _ in range(max(4, len(providers) // 80)):
        rows.append(
            {
                "excl_id": _rid(rng, "EXC"),
                "lastname": fake.last_name(),
                "firstname": fake.first_name(),
                "busname": "",
                "dob": None,  # filled from excl_id below so the RNG stream is unchanged
                "address": fake.street_address(),
                "npi": None if rng.random() < 0.7 else random_npi(rng),
                "excl_type": str(rng.choice(["1128a1", "1128b4", "1128a2"])),
                "excl_date": _add_days(start, -int(rng.integers(30, 400))),
                "rein_date": None,
            }
        )
    for row in rows:
        row["dob"] = _stable_dob(str(row["excl_id"]))
    return pd.DataFrame(rows)


def _stable_dob(key: str) -> date:
    """A date of birth between 1945 and 1984 derived from the record id (no RNG draw)."""
    offset = int.from_bytes(hashlib.sha256(key.encode()).digest()[:4], "big") % (40 * 365)
    return date(1945, 1, 1) + timedelta(days=offset)


def _investigations(ds: Dataset, rng: np.random.Generator, start: date, end: date, spec: Profile) -> None:
    if ds.ground_truth.empty:
        ds.tables["investigation"] = pd.DataFrame()
        ds.tables["investigation_subject"] = pd.DataFrame()
        return
    inv_rows = []
    sub_rows = []
    bad = ds.ground_truth.dropna(subset=["provider_id"])
    n = min(spec.n_investigations, max(1, len(bad)))
    sample = bad.sample(n=n, random_state=int(rng.integers(0, 10_000))) if n else bad
    for _, row in sample.iterrows():
        iid = _rid(rng, "INV")
        opened = _add_days(start, int(rng.integers(20, 200)))
        closed = _add_days(opened, int(rng.integers(10, 80)))
        true_bad = True
        noisy_unsub = true_bad and rng.random() < 0.15
        outcome = "unsubstantiated" if noisy_unsub else str(
            rng.choice(["substantiated", "education", "referred"], p=[0.5, 0.3, 0.2])
        )
        inv_rows.append(
            {
                "investigation_id": iid,
                "opened": opened,
                "closed": closed,
                "lead_source": "data_analysis",
                "scheme_tag": row.scheme_id,
                "outcome": outcome,
                "amount_identified": float(rng.uniform(800, 40_000)),
                "amount_recovered": float(rng.uniform(0, 12_000)),
                "closed_reason": "synthetic historical outcome",
            }
        )
        sub_rows.append({"investigation_id": iid, "provider_id": row.provider_id})
    ds.tables["investigation"] = pd.DataFrame(inv_rows)
    ds.tables["investigation_subject"] = pd.DataFrame(sub_rows)
