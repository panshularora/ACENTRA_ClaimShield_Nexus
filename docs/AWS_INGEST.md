# AWS S3 ingest

ClaimShield keeps detection in the existing FastAPI + worker/core path. AWS is the file drop and trigger.

```
S3 incoming/*.csv
        → Lambda claimshield-s3-processor
        → POST /api/v1/aws/ingest  (X-ClaimShield-Internal-Token)
        → persist_dataset + execute_run
        → PostgreSQL
        → React UI
```

Do not recreate the bucket, Lambda, or CloudWatch dashboard. They already exist in `ap-south-1`.

## Live wiring (hackathon sheet)

| Name | Value |
| --- | --- |
| AWS_REGION | ap-south-1 |
| S3_BUCKET | claimshield-nexus-data-2026 |
| S3_INPUT_PREFIX | incoming/ |
| S3_PROCESSED_PREFIX | processed/ |
| S3_RESULTS_PREFIX | results/ |
| LAMBDA_FUNCTION | claimshield-s3-processor |
| CLAIMSHIELD_API_URL | https://claimshield-nexus-api.vercel.app |

`CLAIMSHIELD_INTERNAL_TOKEN` is set on **both** Lambda and FastAPI and must match. It is never committed, never returned by `GET /api/v1/aws/status`, and never written to logs (the Lambda handler redacts token-like fields).

The API also accepts `CLAIMSHIELD_AWS_REGION`, `CLAIMSHIELD_S3_BUCKET`, `CLAIMSHIELD_S3_INCOMING_PREFIX` (same as `S3_INPUT_PREFIX`), `CLAIMSHIELD_S3_PROCESSED_PREFIX`, `CLAIMSHIELD_S3_RESULTS_PREFIX`, and `CLAIMSHIELD_LAMBDA_FUNCTION`.

## What to upload

The pipeline needs a **full extract directory**, the same CSVs `python -m claimshield generate` writes:

- required: `member.csv`, `provider.csv`, `claim.csv` (or `claims.csv`), `claim_line.csv`
- optional: location, facility, owner, ownership_link, contact_point, referral, evv_visit, rx_fill, eligibility_span, inpatient_stay, exclusion_record, investigation, investigation_subject

Upload them under one prefix, for example:

```
s3://claimshield-nexus-data-2026/incoming/member.csv
s3://claimshield-nexus-data-2026/incoming/provider.csv
s3://claimshield-nexus-data-2026/incoming/claim.csv
s3://claimshield-nexus-data-2026/incoming/claim_line.csv
...
```

Lambda fires once per object. Until the four required tables are present the API returns `waiting_for_tables` and does not run detection. The last required file starts the existing pipeline. A second event for the same files (same ETags) returns `already_processed`.

Never write outputs to `incoming/` (that retriggers Lambda). Summaries go to `results/{batch_id}.json` and a copy of the triggering CSV to `processed/{batch_id}/`.

## Local development (no AWS)

Leave `CLAIMSHIELD_INTERNAL_TOKEN` empty. Manager `POST /api/v1/batches` still loads synthetic data.

To exercise ingest without AWS:

```bash
export CLAIMSHIELD_INTERNAL_TOKEN=dev-only-token
export CLAIMSHIELD_S3_LOCAL_DIR=/tmp/claimshield-s3
mkdir -p /tmp/claimshield-s3/incoming
cp data/generated/tiny/*.csv /tmp/claimshield-s3/incoming/
# then POST /api/v1/aws/ingest with the token header
```

## API auth

Machine header: `X-ClaimShield-Internal-Token: <CLAIMSHIELD_INTERNAL_TOKEN>`

Missing or wrong token → `401` with `internal token required`. The secret is never returned.

## IAM the API needs (when it talks to real S3)

The process running FastAPI needs:

- `s3:GetObject`, `s3:ListBucket` on `claimshield-nexus-data-2026/incoming/`
- `s3:PutObject` on `claimshield-nexus-data-2026/processed/` and `.../results/`

Use an instance/task role or a local AWS profile. Do not commit access keys.

Lambda already has S3 read on incoming and the ObjectCreated trigger. It does not download the CSV; the API does.

## Blocker

Lambda cannot call `http://127.0.0.1:8000`. The API must be on a public HTTPS URL (or a VPC path Lambda can reach) before live S3 uploads will work.
