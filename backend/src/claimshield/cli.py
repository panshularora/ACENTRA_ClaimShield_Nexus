from __future__ import annotations

import argparse
from pathlib import Path

from claimshield.core.config import get_settings
from claimshield.synth.export import generate_and_export


def main() -> None:
    parser = argparse.ArgumentParser(prog="claimshield", description="ClaimShield Nexus CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="Write a synthetic extract to data/generated/")
    gen.add_argument("--profile", default="tiny", choices=["tiny", "small", "panel", "full"])
    gen.add_argument("--seed", type=int, default=7)
    gen.add_argument("--out", type=Path, default=None)

    trn = sub.add_parser("train", help="Train, backtest and register the P(confirm) and 30/60/90 hazard models")
    trn.add_argument("--profile", default="panel", choices=["panel"])
    trn.add_argument("--seed", type=int, default=7)
    trn.add_argument("--worlds", type=int, default=24, help="synthetic worlds (generator seeds)")
    trn.add_argument("--capacity-hours", type=float, default=40.0)
    trn.add_argument("--workers", type=int, default=None)
    trn.add_argument("--no-challenger", action="store_true", help="skip the gradient-boosting challenger")
    trn.add_argument("--out", type=Path, default=None)

    args = parser.parse_args()
    if args.command == "train":
        _train(args)
    elif args.command == "generate":
        settings = get_settings()
        out = args.out or (settings.data_dir / "generated" / args.profile)
        dataset = generate_and_export(args.profile, args.seed, out)
        print(f"wrote {out} lines={dataset.data_card['n_claim_lines']} schemes={dataset.data_card['n_schemes']}")


def _train(args: argparse.Namespace) -> None:
    from claimshield.risk.artifact import default_path
    from claimshield.risk.train import TrainConfig, train

    cfg = TrainConfig(
        profile=args.profile,
        seed=args.seed,
        n_worlds=args.worlds,
        capacity_hours=args.capacity_hours,
        workers=args.workers,
        challenger=not args.no_challenger,
    )
    out = args.out or default_path(get_settings())
    artifact = train(cfg, out)
    hz = artifact["metrics"]["hazard"]["90d"]["model"]
    pc = artifact["metrics"]["confirm"]["model"]
    print(
        f"wrote {out} version={artifact['model_version']} calibrated={artifact['calibrated']} "
        f"seconds={artifact['timing_seconds']['total']}\n"
        f"  hazard 90d: PR-AUC={hz['pr_auc']} Brier={hz['brier']} "
        f"P@cap={hz['precision_at_capacity']} R@cap={hz['recall_at_capacity']}\n"
        f"  P(confirm): PR-AUC={pc['pr_auc']} Brier={pc['brier']} "
        f"P@cap={pc['precision_at_capacity']} R@cap={pc['recall_at_capacity']}"
    )


if __name__ == "__main__":
    main()
