from __future__ import annotations

import json
from pathlib import Path

from claimshield.synth.generator import Dataset, generate


def export_dataset(dataset: Dataset, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, frame in dataset.tables.items():
        frame.to_csv(out_dir / f"{name}.csv", index=False)
    dataset.ground_truth.to_csv(out_dir / "ground_truth.csv", index=False)
    (out_dir / "data_card.json").write_text(
        json.dumps(dataset.data_card, indent=2, default=str),
        encoding="utf-8",
    )
    (out_dir / "README.md").write_text(
        "\n".join(
            [
                f"# ClaimShield synthetic extract ({dataset.profile}, seed={dataset.seed})",
                "",
                "Ground truth is in `ground_truth.csv` and is **not** a feature table.",
                "Do not join scheme labels into model training features.",
                "Codes are SYNTH / HCPCS2 / NDC-SYN only. No CPT.",
                "",
                json.dumps(dataset.data_card, indent=2, default=str),
                "",
            ]
        ),
        encoding="utf-8",
    )
    return out_dir


def generate_and_export(profile: str, seed: int, out_dir: Path) -> Dataset:
    dataset = generate(profile=profile, seed=seed)
    export_dataset(dataset, out_dir)
    return dataset
