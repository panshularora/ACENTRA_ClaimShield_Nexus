from __future__ import annotations

import argparse
from pathlib import Path

from claimshield.core.config import get_settings
from claimshield.synth.export import generate_and_export


def main() -> None:
    parser = argparse.ArgumentParser(prog="claimshield", description="ClaimShield Nexus CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="Write a synthetic extract to data/generated/")
    gen.add_argument("--profile", default="tiny", choices=["tiny", "small", "full"])
    gen.add_argument("--seed", type=int, default=7)
    gen.add_argument("--out", type=Path, default=None)

    args = parser.parse_args()
    if args.command == "generate":
        settings = get_settings()
        out = args.out or (settings.data_dir / "generated" / args.profile)
        dataset = generate_and_export(args.profile, args.seed, out)
        print(f"wrote {out} lines={dataset.data_card['n_claim_lines']} schemes={dataset.data_card['n_schemes']}")


if __name__ == "__main__":
    main()
