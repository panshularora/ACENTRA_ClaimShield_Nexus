# ClaimShield synthetic extract (tiny, seed=7)

Ground truth is in `ground_truth.csv` and is **not** a feature table.
Do not join scheme labels into model training features.
Codes are SYNTH / HCPCS2 / NDC-SYN only. No CPT.

{
  "profile": "tiny",
  "seed": 7,
  "n_members": 120,
  "n_providers": 47,
  "n_claim_lines": 2767,
  "n_schemes": 30,
  "code_systems": [
    "HCPCS2",
    "NDC-SYN",
    "SYNTH"
  ],
  "base_rates": "design knobs, not prevalence estimates",
  "limitations": [
    "synthetic data",
    "no medical records",
    "labels partial and noisy"
  ]
}
