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
    # Spread scheme onsets over the window (seeded) instead of fixed day offsets. Used by the
    # training panel so the 30/60/90 hazard has onsets and continuations across months.
    onset_spread: bool = False


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
    # Many small worlds (one per seed) for training and backtesting the risk models. Fifteen
    # 30-day months give rolling origins with a full 90-day label window and a purge gap.
    "panel": Profile(
        name="panel",
        n_members=260,
        n_providers=48,
        n_locations=24,
        n_owners=26,
        n_months=15,
        target_lines=5600,
        n_referrals=340,
        n_evv=0,
        n_rx=560,
        n_investigations=12,
        onset_spread=True,
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
