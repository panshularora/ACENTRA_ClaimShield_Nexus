"""Plant literature-backed FWA schemes into a Dataset.

Sources (see data/reference/PAPERS.md):
S01 OIG NH duplicates; S02 OIG E/M upcoding; S03 NCCI unbundling;
S04 MUE excess units; S05 phantom after death; S06 ambulance OEI-09-12-00351;
S07 impossible timing / Krizek / DOJ 2026; S08 ABA during inpatient (OIG);
S09 EVV / 21st Century Cures; S10 OIG home health IQR fence;
S11 LEIE excluded parties; S12 OIG doctor shopping OEI-02-17-00250;
G1 OIG telefraud SFA 2022 + Gold Rush; G2 recruiter/sober-home rings;
G3 straw owners / 42 CFR 455.104; C1 metric gaming (DOJ 2026 hospice);
S13 POS mismatch; S14 sex/age implausible; S15 weekend mill;
S16 geodesic mileage padding; S17 referral HHI monopoly;
S18 clone billing; S19 stay compression (Schrupp 2024 analogue);
S20 principal diagnosis swap analogue (Schrupp ICD order).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd
from faker import Faker

from claimshield.synth.codes import (
    ABA_HOUR,
    AMB_MILEAGE,
    CODE_SYSTEM_HCPCS2,
    CODE_SYSTEM_NDC,
    CODE_SYSTEM_SYNTH,
    DME_CATH,
    EM_LEVELS,
    HOME_VISIT,
    LAB_PANEL,
    POS_HOME,
    POS_INPATIENT,
    POS_OFFICE,
)
from claimshield.synth.luhn import random_npi
from claimshield.synth.profiles import Profile

if TYPE_CHECKING:
    from claimshield.synth.generator import Dataset

ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _rid(rng: np.random.Generator, prefix: str, n: int = 10) -> str:
    return prefix + "-" + "".join(ALPHABET[int(rng.integers(0, len(ALPHABET)))] for _ in range(n))


def _gt_row(**kwargs: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "scheme_id": "",
        "scheme_type": "",
        "variant": "A",
        "provider_id": None,
        "entity_ids": [],
        "line_ids": [],
        "member_ids": [],
        "start": None,
        "end": None,
        "held_out": False,
        "is_fraud": True,
        "notes": "",
    }
    base.update(kwargs)
    return base


def _as_date(value: date | datetime | pd.Timestamp) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    converted: date = pd.Timestamp(value).date()
    return converted


def _append_line(
    ds: Dataset,
    rng: np.random.Generator,
    *,
    provider_id: str,
    member_id: str,
    dos: date,
    code: str,
    code_system: str = CODE_SYSTEM_SYNTH,
    units: float = 1.0,
    minutes: int | None = None,
    mileage: float | None = None,
    modifiers: list[str] | None = None,
    pos: str = POS_OFFICE,
    claim_type: str = "professional",
    paid: float = 120.0,
    dx: list[str] | None = None,
    ordering_id: str | None = None,
) -> str:
    dos = _as_date(dos)
    claim_id = _rid(rng, "CLM")
    line_id = _rid(rng, "LN")
    received = dos + timedelta(days=int(rng.integers(1, 20)))
    claim = {
        "claim_id": claim_id,
        "claim_type": claim_type,
        "member_id": member_id,
        "billing_provider_id": provider_id,
        "facility_id": None,
        "admit": None,
        "discharge": None,
        "received_date": received,
        "adjudicated_date": received + timedelta(days=3),
        "status": "paid",
        "source_system": "generator",
        "source_ref": None,
    }
    line = {
        "line_id": line_id,
        "claim_id": claim_id,
        "rendering_provider_id": provider_id,
        "ordering_provider_id": ordering_id or provider_id,
        "dos_from": dos,
        "dos_to": dos,
        "code_system": code_system,
        "code": code,
        "modifiers": modifiers or [],
        "units": units,
        "minutes": minutes,
        "mileage": mileage,
        "dx": dx or ["SYN-DX-01"],
        "pos": pos,
        "charge": round(paid * 1.2, 2),
        "allowed": round(paid * 1.05, 2),
        "paid": paid,
    }
    ds.tables["claim"] = pd.concat([ds.tables["claim"], pd.DataFrame([claim])], ignore_index=True)
    ds.tables["claim_line"] = pd.concat([ds.tables["claim_line"], pd.DataFrame([line])], ignore_index=True)
    return line_id


def _schedule(
    rng: np.random.Generator,
    spec: Profile,
    start: date,
    end: date,
    *,
    offset: int,
    n: int,
    gap: float,
) -> list[date]:
    """Service dates for an n-line scheme.

    Default profiles keep the fixed offsets (so tiny/small stay byte-identical). A profile with
    ``onset_spread`` draws a seeded onset anywhere in the window and stretches the spacing, so
    schemes start in different months and run for weeks to months. That gives the 30/60/90
    hazard model onsets and continuations to learn from.
    """
    if not spec.onset_spread:
        return [start + timedelta(days=int(offset + i * gap)) for i in range(n)]
    span = (end - start).days
    step = max(1.0, gap) * float(rng.uniform(2.0, 5.0))
    length = round((n - 1) * step)
    latest = max(offset + 2, span - length - 5)
    onset = int(rng.integers(min(offset, latest - 1), latest))
    return [start + timedelta(days=min(span - 1, int(onset + i * step))) for i in range(n)]


def _providers_by_line(ds: Dataset, line: str) -> pd.DataFrame:
    frame = ds.tables["provider"]
    subset = frame[frame.service_line == line]
    return subset if not subset.empty else frame


def plant_all_schemes(
    ds: Dataset,
    rng: np.random.Generator,
    fake: Faker,
    start: date,
    end: date,
    spec: Profile,
) -> None:
    gt: list[dict[str, Any]] = []
    members = ds.tables["member"]
    living = members[members["date_of_death"].isna()]
    if living.empty:
        living = members
    span = max(20, (end - start).days - 15)

    def pick_member() -> str:
        return str(living.iloc[int(rng.integers(0, len(living)))].member_id)

    def pick_dos(offset: int = 30) -> date:
        return start + timedelta(days=int(rng.integers(offset, span)))

    # S01 duplicate billing
    prov = _providers_by_line(ds, "pharmacy").iloc[0]
    m = pick_member()
    dos = pick_dos()
    a = _append_line(ds, rng, provider_id=prov.provider_id, member_id=m, dos=dos, code="NDC-OPIOID-01",
                     code_system=CODE_SYSTEM_NDC, claim_type="pharmacy", paid=64.4)
    b = _append_line(ds, rng, provider_id=prov.provider_id, member_id=m, dos=dos, code="NDC-OPIOID-01",
                     code_system=CODE_SYSTEM_NDC, claim_type="pharmacy", paid=64.11)
    gt.append(_gt_row(scheme_id="S01", scheme_type="duplicate_billing", variant="A",
                      provider_id=prov.provider_id, line_ids=[a, b], member_ids=[m], start=dos, end=dos))
    m2 = pick_member()
    dos2 = pick_dos()
    c = _append_line(ds, rng, provider_id=prov.provider_id, member_id=m2, dos=dos2, code="NDC-OPIOID-01",
                     code_system=CODE_SYSTEM_NDC, claim_type="pharmacy", paid=70.3)
    d = _append_line(ds, rng, provider_id=prov.provider_id, member_id=m2, dos=dos2, code="NDC-OPIOID-01",
                     code_system=CODE_SYSTEM_NDC, claim_type="pharmacy", modifiers=["JW"], paid=71.8)
    gt.append(_gt_row(scheme_id="S01", scheme_type="duplicate_billing", variant="B",
                      provider_id=prov.provider_id, line_ids=[c, d], member_ids=[m2], start=dos2, end=dos2,
                      notes="modifier-shifted near duplicate"))

    # S02 E/M upcoding
    prof = _providers_by_line(ds, "professional").iloc[0]
    line_ids = []
    mids = []
    for _ in range(18):
        mem = pick_member()
        mids.append(mem)
        line_ids.append(
            _append_line(ds, rng, provider_id=prof.provider_id, member_id=mem, dos=pick_dos(),
                         code="EM-EST-5", paid=220.0)
        )
    gt.append(_gt_row(scheme_id="S02", scheme_type="upcoding", variant="A",
                      provider_id=prof.provider_id, line_ids=line_ids, member_ids=mids))
    prof_b = _providers_by_line(ds, "professional").iloc[min(1, len(_providers_by_line(ds, "professional")) - 1)]
    line_ids_b = []
    drift_dates = _schedule(rng, spec, start, end, offset=40, n=16, gap=6)
    for i in range(16):
        code = EM_LEVELS[min(4, 2 + i // 4)]
        line_ids_b.append(
            _append_line(ds, rng, provider_id=prof_b.provider_id, member_id=pick_member(),
                         dos=drift_dates[i], code=code, paid=150 + 15 * i)
        )
    gt.append(_gt_row(scheme_id="S02", scheme_type="upcoding", variant="B",
                      provider_id=prof_b.provider_id, line_ids=line_ids_b, notes="gradual drift"))

    # S03 unbundling
    lab = _providers_by_line(ds, "laboratory").iloc[0]
    mem = pick_member()
    dos = pick_dos()
    l1 = _append_line(ds, rng, provider_id=lab.provider_id, member_id=mem, dos=dos, code=LAB_PANEL,
                      claim_type="laboratory", paid=90)
    l2 = _append_line(ds, rng, provider_id=lab.provider_id, member_id=mem, dos=dos, code="LAB-CMP-03",
                      claim_type="laboratory", paid=40)
    gt.append(_gt_row(scheme_id="S03", scheme_type="unbundling", variant="A",
                      provider_id=lab.provider_id, line_ids=[l1, l2], member_ids=[mem], start=dos, end=dos))

    # S04 excess units (ambulance mileage)
    amb = _providers_by_line(ds, "ambulance").iloc[0]
    line_id = _append_line(ds, rng, provider_id=amb.provider_id, member_id=pick_member(), dos=pick_dos(),
                     code=AMB_MILEAGE, code_system=CODE_SYSTEM_HCPCS2, units=310, mileage=310,
                     claim_type="ambulance", paid=2800, pos="41")
    gt.append(_gt_row(scheme_id="S04", scheme_type="excess_units", variant="A",
                      provider_id=amb.provider_id, line_ids=[line_id], held_out=False))
    dos = pick_dos()
    mem = pick_member()
    split = [
        _append_line(ds, rng, provider_id=amb.provider_id, member_id=mem, dos=dos, code=AMB_MILEAGE,
                     code_system=CODE_SYSTEM_HCPCS2, units=160, mileage=160, claim_type="ambulance", paid=1400, pos="41"),
        _append_line(ds, rng, provider_id=amb.provider_id, member_id=mem, dos=dos, code=AMB_MILEAGE,
                     code_system=CODE_SYSTEM_HCPCS2, units=140, mileage=140, claim_type="ambulance", paid=1200, pos="41"),
    ]
    gt.append(_gt_row(scheme_id="S04", scheme_type="excess_units", variant="B",
                      provider_id=amb.provider_id, line_ids=split, notes="split across lines same day"))

    # S05 after death — decedents are planted in the member table before claims
    dead = members[members.date_of_death.notna()]
    if dead.empty:
        raise RuntimeError("generator must plant decedents before claims")
    decedent = dead.iloc[0]
    dme = _providers_by_line(ds, "dme").iloc[0]
    after = decedent.date_of_death + timedelta(days=12)
    line_id = _append_line(ds, rng, provider_id=dme.provider_id, member_id=decedent.member_id, dos=after,
                     code=DME_CATH, claim_type="dme", paid=310, pos=POS_HOME)
    gt.append(_gt_row(scheme_id="S05", scheme_type="phantom_after_death", variant="A",
                      provider_id=dme.provider_id, line_ids=[line_id], member_ids=[decedent.member_id]))

    # S06 ambulance overlapping / no destination (HELD OUT)
    # With spread onsets it goes on a second ambulance supplier so the held-out type can be
    # scored without the S04/S16 lines on the first one.
    amb_lines = _providers_by_line(ds, "ambulance")
    s06 = amb_lines.iloc[1] if spec.onset_spread and len(amb_lines) > 1 else amb
    mem = pick_member()
    dos = pick_dos()
    a = _append_line(ds, rng, provider_id=s06.provider_id, member_id=mem, dos=dos, code=AMB_MILEAGE,
                     code_system=CODE_SYSTEM_HCPCS2, units=22, mileage=22, minutes=90,
                     claim_type="ambulance", paid=400, pos="41")
    b = _append_line(ds, rng, provider_id=s06.provider_id, member_id=pick_member(), dos=dos, code=AMB_MILEAGE,
                     code_system=CODE_SYSTEM_HCPCS2, units=30, mileage=30, minutes=90,
                     claim_type="ambulance", paid=480, pos="41")
    gt.append(_gt_row(scheme_id="S06", scheme_type="ambulance_impossible", variant="A",
                      provider_id=s06.provider_id, line_ids=[a, b], held_out=True,
                      notes="overlapping trips same vehicle-day"))

    # S07 >24h behavioral (28 billed hours on one clinician-day)
    bh = _providers_by_line(ds, "behavioral_health").iloc[0]
    dos = pick_dos()
    ids = []
    for _ in range(28):
        ids.append(
            _append_line(ds, rng, provider_id=bh.provider_id, member_id=pick_member(), dos=dos,
                         code="PSY-60", minutes=60, units=1, claim_type="behavioral_health", paid=95)
        )
    gt.append(_gt_row(scheme_id="S07", scheme_type="impossible_timing", variant="A",
                      provider_id=bh.provider_id, line_ids=ids, start=dos, end=dos,
                      notes="28 billed PSY-60 hours / 1680 minutes on one day"))

    # S08 ABA during inpatient
    if not ds.tables["inpatient_stay"].empty:
        stay = ds.tables["inpatient_stay"].iloc[0]
        line_id = _append_line(ds, rng, provider_id=bh.provider_id, member_id=stay.member_id,
                         dos=stay.admit, code=ABA_HOUR, minutes=60, claim_type="behavioral_health",
                         paid=110, pos=POS_OFFICE)
        gt.append(_gt_row(scheme_id="S08", scheme_type="inpatient_overlap", variant="A",
                          provider_id=bh.provider_id, line_ids=[line_id], member_ids=[stay.member_id]))

    # S09 missing EVV — use a different agency than S10 so the case stays EVV-only
    hh_all = _providers_by_line(ds, "home_health")
    hh_s09 = hh_all.iloc[min(2, len(hh_all) - 1)]
    mem = pick_member()
    dos = pick_dos()
    line_id = _append_line(ds, rng, provider_id=hh_s09.provider_id, member_id=mem, dos=dos, code=HOME_VISIT,
                     minutes=60, claim_type="home_health", paid=88, pos=POS_HOME)
    gt.append(_gt_row(scheme_id="S09", scheme_type="evv_missing", variant="A",
                      provider_id=hh_s09.provider_id, line_ids=[line_id], member_ids=[mem],
                      notes="home visit with no EVV row"))

    # S10 excessive home health visits vs peers
    hh = hh_all.iloc[0]
    ids = []
    heavy_member = pick_member()
    visit_dates = _schedule(rng, spec, start, end, offset=60, n=28, gap=1)
    for i in range(28):
        ids.append(
            _append_line(ds, rng, provider_id=hh.provider_id, member_id=heavy_member,
                         dos=visit_dates[i], code=HOME_VISIT, minutes=45,
                         claim_type="home_health", paid=92, pos=POS_HOME)
        )
    gt.append(_gt_row(scheme_id="S10", scheme_type="excessive_utilization", variant="A",
                      provider_id=hh.provider_id, line_ids=ids, member_ids=[heavy_member]))

    # S11 excluded party
    excl = ds.tables["exclusion_record"].iloc[0]
    target = ds.tables["provider"].iloc[-1]
    excl_npi = excl.npi if pd.notna(excl.npi) and excl.npi else None
    npi = str(excl_npi or target.npi_syn)
    ds.tables["provider"].loc[
        ds.tables["provider"].provider_id == target.provider_id, "npi_syn"
    ] = npi
    # The LEIE row describes the same party as the provider record: NPI and name agree.
    is_row = ds.tables["exclusion_record"].excl_id == excl.excl_id
    ds.tables["exclusion_record"].loc[is_row, "npi"] = npi
    ds.tables["exclusion_record"].loc[is_row, ["firstname", "lastname", "busname"]] = _leie_name(target["name"])
    line_id = _append_line(ds, rng, provider_id=target.provider_id, member_id=pick_member(),
                     dos=pick_dos(), code="EM-EST-3", paid=130)
    gt.append(_gt_row(scheme_id="S11", scheme_type="excluded_party", variant="A",
                      provider_id=target.provider_id, line_ids=[line_id],
                      notes="billing NPI matches synthetic LEIE row"))

    # S12 doctor shopping
    member = pick_member()
    prescribers = _providers_by_line(ds, "professional")["provider_id"].tolist()[:5]
    pharmacies = _providers_by_line(ds, "pharmacy")["provider_id"].tolist()[:5]
    rx_rows = []
    fill_dates = _schedule(rng, spec, start, end, offset=70, n=5, gap=12)
    for i in range(5):
        rx_rows.append(
            {
                "member_id": member,
                "prescriber_id": prescribers[i % len(prescribers)],
                "pharmacy_id": pharmacies[i % len(pharmacies)],
                "drug_class_syn": "opioid",
                "days_supply": 30,
                "qty": 90,
                "mme": 140,
                "fill_date": fill_dates[i],
            }
        )
    ds.tables["rx_fill"] = pd.concat([ds.tables["rx_fill"], pd.DataFrame(rx_rows)], ignore_index=True)
    gt.append(_gt_row(scheme_id="S12", scheme_type="doctor_shopping", variant="A",
                      provider_id=prescribers[0], member_ids=[member], entity_ids=prescribers + pharmacies))

    # G1 telefraud ring — every claim passes single-claim rules
    g1 = _plant_ring(ds, rng, fake, start, kind="telefraud",
                     dates=_schedule(rng, spec, start, end, offset=40, n=24, gap=1),
                     spread=spec.onset_spread)
    gt.append(g1)
    # G2 sober-home
    gt.append(_plant_ring(ds, rng, fake, start, kind="sober_home",
                          dates=_schedule(rng, spec, start, end, offset=40, n=24, gap=1),
                          spread=spec.onset_spread))
    # G3 shell cluster
    gt.append(_plant_shell(ds, rng, fake, start,
                           dates=_schedule(rng, spec, start, end, offset=20, n=15, gap=1),
                           spread=spec.onset_spread))

    # C1 camouflaged: just under thresholds
    cam = _providers_by_line(ds, "home_health").iloc[min(1, len(_providers_by_line(ds, "home_health")) - 1)]
    ids = []
    cam_dates = _schedule(rng, spec, start, end, offset=90, n=14, gap=2)
    for i in range(14):
        ids.append(
            _append_line(ds, rng, provider_id=cam.provider_id, member_id=pick_member(),
                         dos=cam_dates[i], code=HOME_VISIT, minutes=40,
                         units=3, claim_type="home_health", paid=85, pos=POS_HOME)
        )
    gt.append(_gt_row(scheme_id="C1", scheme_type="camouflaged", variant="A",
                      provider_id=cam.provider_id, line_ids=ids,
                      notes="metrics just under unit cap and 24h"))

    # Extra literature schemes
    # S13 POS mismatch: office code billed inpatient
    line_id = _append_line(ds, rng, provider_id=prof.provider_id, member_id=pick_member(), dos=pick_dos(),
                     code="EM-EST-4", pos=POS_INPATIENT, paid=240)
    gt.append(_gt_row(scheme_id="S13", scheme_type="pos_mismatch", variant="A",
                      provider_id=prof.provider_id, line_ids=[line_id]))

    # S14 sex-implausible: prostate-related synth code on female
    female = living[living.sex == "F"].iloc[0]
    line_id = _append_line(ds, rng, provider_id=prof.provider_id, member_id=female.member_id, dos=pick_dos(),
                     code="PROC-MALE-01", paid=800, dx=["SYN-DX-PROSTATE"])
    gt.append(_gt_row(scheme_id="S14", scheme_type="sex_implausible", variant="A",
                      provider_id=prof.provider_id, line_ids=[line_id], member_ids=[female.member_id]))

    # S15 weekend mill for office-only
    weekend = start + timedelta(days=((5 - start.weekday()) % 7) + 14)
    if spec.onset_spread:
        weeks_left = max(1, ((end - weekend).days - 7 * 8) // 7)
        weekend += timedelta(days=7 * int(rng.integers(0, weeks_left)))
    ids = [
        _append_line(ds, rng, provider_id=prof.provider_id, member_id=pick_member(), dos=weekend + timedelta(days=7 * i),
                     code="EM-EST-4", paid=180)
        for i in range(8)
    ]
    gt.append(_gt_row(scheme_id="S15", scheme_type="weekend_mill", variant="A",
                      provider_id=prof.provider_id, line_ids=ids))

    # S16 mileage vs plausible distance
    line_id = _append_line(ds, rng, provider_id=amb.provider_id, member_id=pick_member(), dos=pick_dos(),
                     code=AMB_MILEAGE, code_system=CODE_SYSTEM_HCPCS2, units=180, mileage=180,
                     claim_type="ambulance", paid=1600, pos="41")
    gt.append(_gt_row(scheme_id="S16", scheme_type="mileage_padding", variant="A",
                      provider_id=amb.provider_id, line_ids=[line_id], notes="urban trip billed 180 miles"))

    # S17 concentrated referrals
    rec = _providers_by_line(ds, "dme").iloc[0]
    ref = _providers_by_line(ds, "professional").iloc[0]
    ref_rows = [
        {
            "referring_id": ref.provider_id,
            "receiving_id": rec.provider_id,
            "member_id": pick_member(),
            "date": pick_dos(),
            "kind": "order",
        }
        for _ in range(40)
    ]
    ds.tables["referral"] = pd.concat([ds.tables["referral"], pd.DataFrame(ref_rows)], ignore_index=True)
    gt.append(_gt_row(scheme_id="S17", scheme_type="referral_monopoly", variant="A",
                      provider_id=rec.provider_id, entity_ids=[ref.provider_id, rec.provider_id]))

    # S18 clone billing
    clone_ids = []
    pattern_dos = pick_dos()
    for _ in range(12):
        clone_ids.append(
            _append_line(ds, rng, provider_id=prof.provider_id, member_id=pick_member(),
                         dos=pattern_dos, code="EM-EST-4", minutes=None, paid=187.37, dx=["SYN-DX-01", "SYN-DX-02"])
        )
    gt.append(_gt_row(scheme_id="S18", scheme_type="clone_billing", variant="A",
                      provider_id=prof.provider_id, line_ids=clone_ids))

    # S19 stay compression analogue (Schrupp reducing duration / bloody release)
    if fac_ok(ds):
        stay_m = pick_member()
        fac = ds.tables["facility"].iloc[0].facility_id
        same_day = pick_dos()
        ds.tables["inpatient_stay"] = pd.concat(
            [
                ds.tables["inpatient_stay"],
                pd.DataFrame(
                    [{"member_id": stay_m, "facility_id": fac, "admit": same_day, "discharge": same_day}]
                ),
            ],
            ignore_index=True,
        )
        fac_prov = _providers_by_line(ds, "facility").iloc[0]
        line_id = _append_line(ds, rng, provider_id=fac_prov.provider_id,
                         member_id=stay_m, dos=same_day, code="FAC-DRG-HI", claim_type="facility",
                         paid=18000, pos=POS_INPATIENT)
        gt.append(_gt_row(scheme_id="S19", scheme_type="stay_compression", variant="A",
                          provider_id=fac_prov.provider_id, line_ids=[line_id],
                          notes="Schrupp 2024 analogue: high DRG, same-day discharge"))

    # S20 diagnosis order swap analogue
    line_id = _append_line(ds, rng, provider_id=prof.provider_id, member_id=pick_member(), dos=pick_dos(),
                     code="EM-EST-5", paid=260, dx=["SYN-DX-COMPLEX", "SYN-DX-01"])
    gt.append(_gt_row(scheme_id="S20", scheme_type="dx_order_swap", variant="A",
                      provider_id=prof.provider_id, line_ids=[line_id],
                      notes="Schrupp ICD-order analogue using synthetic dx"))

    # S21 genetic testing mill (OIG consumer alert analogue)
    gen_ids = []
    gen_members = []
    gen_dates = _schedule(rng, spec, start, end, offset=50, n=22, gap=1)
    for i in range(22):
        mem = pick_member()
        gen_members.append(mem)
        gen_ids.append(
            _append_line(ds, rng, provider_id=lab.provider_id, member_id=mem,
                         dos=gen_dates[i], code="LAB-GEN-01",
                         claim_type="laboratory", paid=2100)
        )
    gt.append(_gt_row(scheme_id="S21", scheme_type="genetic_mill", variant="A",
                      provider_id=lab.provider_id, line_ids=gen_ids, member_ids=gen_members,
                      notes="OIG genetic-testing scam analogue: high-cost panels, many members, short window"))

    # Hard negatives: high volume that is still legitimate (eval false-positive fence)
    hn = _providers_by_line(ds, "professional").iloc[min(2, len(_providers_by_line(ds, "professional")) - 1)]
    hn_ids = [
        _append_line(ds, rng, provider_id=hn.provider_id, member_id=pick_member(),
                     dos=pick_dos(), code="EM-EST-3", paid=118)
        for _ in range(36)
    ]
    gt.append(_gt_row(scheme_id="HN1", scheme_type="hard_negative", variant="A",
                      provider_id=hn.provider_id, line_ids=hn_ids, is_fraud=False,
                      notes="high-volume established-patient level 3; not upcoding"))
    mem = pick_member()
    dos = pick_dos()
    hn_panel = _append_line(ds, rng, provider_id=lab.provider_id, member_id=mem, dos=dos,
                            code=LAB_PANEL, claim_type="laboratory", paid=90)
    hn_ok = _append_line(ds, rng, provider_id=lab.provider_id, member_id=mem, dos=dos,
                         code="LAB-CMP-05", claim_type="laboratory", paid=22)
    gt.append(_gt_row(scheme_id="HN2", scheme_type="hard_negative", variant="A",
                      provider_id=lab.provider_id, line_ids=[hn_panel, hn_ok], is_fraud=False,
                      notes="PTP indicator-1 pair billed together is allowed"))

    ds.ground_truth = pd.DataFrame(gt)


def fac_ok(ds: Dataset) -> bool:
    return not ds.tables["facility"].empty


def _plant_ring(
    ds: Dataset,
    rng: np.random.Generator,
    fake: Faker,
    start: date,
    *,
    kind: str,
    dates: list[date],
    spread: bool,
) -> dict[str, Any]:
    loc_id = ds.tables["location"].iloc[0].location_id
    owner_id = _rid(rng, "OWN")
    owners = pd.DataFrame(
        [{"owner_id": owner_id, "kind": "person", "name": fake.name(), "dob": date(1972, 4, 4)}]
    )
    ds.tables["owner"] = pd.concat([ds.tables["owner"], owners], ignore_index=True)
    new_provs = []
    n = 3
    line = "dme" if kind == "telefraud" else "behavioral_health"
    enrolled = dates[0] - timedelta(days=30) if spread else start + timedelta(days=10)
    linked = enrolled if spread else start
    for _ in range(n):
        pid = _rid(rng, "PRV")
        new_provs.append(
            {
                "provider_id": pid,
                "npi_syn": random_npi(rng),
                "name": fake.company(),
                "kind": "organization",
                "specialty": "dme_supplier" if kind == "telefraud" else "sud_clinic",
                "service_line": line,
                "location_id": loc_id,
                "enroll_date": enrolled,
                "term_date": None,
                "tin_token": "TIN-RING1" if kind == "telefraud" else "TIN-RING2",
                "rural": False,
                "sole_community": False,
            }
        )
        ds.tables["ownership_link"] = pd.concat(
            [
                ds.tables["ownership_link"],
                pd.DataFrame(
                    [{"owner_id": owner_id, "provider_id": pid, "pct": 80.0, "start": linked, "end": None}]
                ),
            ],
            ignore_index=True,
        )
        ds.tables["contact_point"] = pd.concat(
            [
                ds.tables["contact_point"],
                pd.DataFrame(
                    [
                        {
                            "entity_id": pid,
                            "entity_type": "provider",
                            "kind": "bank_token",
                            "value_hash": "BK-SHARED-RING",
                        }
                    ]
                ),
            ],
            ignore_index=True,
        )
    ds.tables["provider"] = pd.concat([ds.tables["provider"], pd.DataFrame(new_provs)], ignore_index=True)
    orderer = _providers_by_line(ds, "professional").iloc[0].provider_id
    living_ids = ds.tables["member"][ds.tables["member"]["date_of_death"].isna()]["member_id"].tolist()
    if not living_ids:
        living_ids = ds.tables["member"]["member_id"].tolist()
    line_ids = []
    member_ids = []
    for i in range(24):
        mem = str(living_ids[int(rng.integers(0, len(living_ids)))])
        member_ids.append(mem)
        pid = new_provs[i % n]["provider_id"]
        code = DME_CATH if kind == "telefraud" else "PSY-60"
        line_ids.append(
            _append_line(
                ds,
                rng,
                provider_id=pid,
                member_id=mem,
                dos=dates[i],
                code=code,
                minutes=45 if kind != "telefraud" else None,
                claim_type=line,
                paid=95.0,
                ordering_id=orderer,
                pos=POS_HOME if kind == "telefraud" else POS_OFFICE,
            )
        )
        ds.tables["referral"] = pd.concat(
            [
                ds.tables["referral"],
                pd.DataFrame(
                    [
                        {
                            "referring_id": orderer,
                            "receiving_id": pid,
                            "member_id": mem,
                            "date": dates[i],
                            "kind": "order",
                        }
                    ]
                ),
            ],
            ignore_index=True,
        )
    return _gt_row(
        scheme_id="G1" if kind == "telefraud" else "G2",
        scheme_type=kind,
        variant="A",
        provider_id=new_provs[0]["provider_id"],
        entity_ids=[p["provider_id"] for p in new_provs] + [owner_id, orderer],
        line_ids=line_ids,
        member_ids=member_ids,
        notes="claims individually pass hard rules; ring is the signal",
    )


def _leie_name(name: str) -> list[str]:
    """Split a provider name into LEIE first/last/business fields (no RNG draw)."""
    parts = str(name).split()
    is_person = len(parts) == 2 and not any(p.rstrip(",").lower() in {"inc", "llc", "group", "and"} for p in parts)
    return [parts[0], parts[1], ""] if is_person else ["", "", str(name)]


def _plant_shell(
    ds: Dataset,
    rng: np.random.Generator,
    fake: Faker,
    start: date,
    *,
    dates: list[date],
    spread: bool,
) -> dict[str, Any]:
    location = ds.tables["location"].iloc[1 % len(ds.tables["location"])]
    loc_id = location.location_id
    excl = ds.tables["exclusion_record"].iloc[min(1, len(ds.tables["exclusion_record"]) - 1)]
    # The excluded owner's address on the LEIE row is the shell suite: name, DOB and address agree.
    ds.tables["exclusion_record"].loc[
        ds.tables["exclusion_record"].excl_id == excl.excl_id, "address"
    ] = location.address_norm
    owner_id = _rid(rng, "OWN")
    ds.tables["owner"] = pd.concat(
        [
            ds.tables["owner"],
            pd.DataFrame(
                [
                    {
                        "owner_id": owner_id,
                        "kind": "person",
                        "name": f"{excl.firstname} {excl.lastname}",
                        "dob": excl.dob,
                    }
                ]
            ),
        ],
        ignore_index=True,
    )
    pids = []
    enrolled = dates[0] - timedelta(days=30) if spread else start + timedelta(days=5)
    linked = enrolled if spread else start
    for _ in range(5):
        pid = _rid(rng, "PRV")
        pids.append(pid)
        ds.tables["provider"] = pd.concat(
            [
                ds.tables["provider"],
                pd.DataFrame(
                    [
                        {
                            "provider_id": pid,
                            "npi_syn": random_npi(rng),
                            "name": fake.company(),
                            "kind": "organization",
                            "specialty": "home_health_agency",
                            "service_line": "home_health",
                            "location_id": loc_id,
                            "enroll_date": enrolled,
                            "term_date": None,
                            "tin_token": "TIN-SHELL",
                            "rural": False,
                            "sole_community": False,
                        }
                    ]
                ),
            ],
            ignore_index=True,
        )
        ds.tables["ownership_link"] = pd.concat(
            [
                ds.tables["ownership_link"],
                pd.DataFrame(
                    [{"owner_id": owner_id, "provider_id": pid, "pct": 100.0, "start": linked, "end": None}]
                ),
            ],
            ignore_index=True,
        )
    living_ids = ds.tables["member"][ds.tables["member"]["date_of_death"].isna()]["member_id"].tolist()
    if not living_ids:
        living_ids = ds.tables["member"]["member_id"].tolist()
    line_ids = [
        _append_line(
            ds,
            rng,
            provider_id=pids[i % 5],
            member_id=str(living_ids[i % len(living_ids)]),
            dos=dates[i],
            code=HOME_VISIT,
            minutes=40,
            claim_type="home_health",
            paid=77,
            pos=POS_HOME,
        )
        for i in range(15)
    ]
    return _gt_row(
        scheme_id="G3",
        scheme_type="shell_cluster",
        variant="A",
        provider_id=pids[0],
        entity_ids=[*pids, owner_id],
        line_ids=line_ids,
        notes="five NPIs one suite; owner name matches exclusion record",
    )
