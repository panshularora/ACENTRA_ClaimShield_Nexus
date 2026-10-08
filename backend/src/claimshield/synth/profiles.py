from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Profile:
    name: str
    n_members: int
    n_providers: int
    n_locations: int
    n_owners: int
    n_months: int
    target_lines: int
    n_referrals: int
    n_evv: int
    n_rx: int
    n_investigations: int
    fraud_provider_rate: float = 0.03
    fraud_line_rate: float = 0.01


PROFILES: dict[str, Profile] = {
    "tiny": Profile(
        name="tiny",
        n_members=120,
        n_providers=36,
        n_locations=18,
        n_owners=20,
        n_months=8,
        target_lines=2500,
        n_referrals=180,
        n_evv=220,
        n_rx=300,
        n_investigations=12,
    ),
    "small": Profile(
        name="small",
        n_members=6000,
        n_providers=320,
        n_locations=90,
        n_owners=120,
        n_months=18,
        target_lines=150_000,
        n_referrals=18_000,
        n_evv=24_000,
        n_rx=40_000,
        n_investigations=80,
    ),
    "full": Profile(
        name="full",
        n_members=20_000,
        n_providers=1000,
        n_locations=300,
        n_owners=400,
        n_months=24,
        target_lines=800_000,
        n_referrals=60_000,
        n_evv=80_000,
        n_rx=150_000,
        n_investigations=150,
    ),
}
