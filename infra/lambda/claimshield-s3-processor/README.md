# claimshield-s3-processor

Thin Lambda: S3 ObjectCreated on `incoming/*.csv` → authenticated `POST /api/v1/aws/ingest`.

The fraud pipeline stays in the ClaimShield API. This function only validates the object, calls the API, and writes structured logs.

## Environment

| Variable | Required | Purpose |
| --- | --- | --- |
| `CLAIMSHIELD_API_URL` | yes | Public base URL of the FastAPI app (no trailing path) |
| `CLAIMSHIELD_INTERNAL_TOKEN` | yes | Same secret as the API `CLAIMSHIELD_INTERNAL_TOKEN` |
| `CLAIMSHIELD_S3_BUCKET` or `S3_BUCKET` | no | Default `claimshield-nexus-data-2026` |
| `CLAIMSHIELD_S3_INCOMING_PREFIX` or `S3_INPUT_PREFIX` | no | Default `incoming/` |
| `CLAIMSHIELD_ENVIRONMENT` | no | CloudWatch EMF dimension, default `hackathon` |

The FastAPI process uses the same bucket and prefixes (`processed/`, `results/`). Lambda and FastAPI **must** share one `CLAIMSHIELD_INTERNAL_TOKEN`. Do not commit it.

Do not put AWS access keys in this function. Use the existing execution role.

## Deploy (existing function, do not recreate)

```bash
cd infra/lambda/claimshield-s3-processor
zip -j /tmp/claimshield-s3-processor.zip handler.py
aws lambda update-function-code \
  --region ap-south-1 \
  --function-name claimshield-s3-processor \
  --zip-file fileb:///tmp/claimshield-s3-processor.zip
aws lambda update-function-configuration \
  --region ap-south-1 \
  --function-name claimshield-s3-processor \
  --timeout 120 \
  --memory-size 256 \
  --environment "Variables={CLAIMSHIELD_API_URL=https://claimshield-nexus-api.vercel.app,CLAIMSHIELD_INTERNAL_TOKEN=YOUR-SECRET,CLAIMSHIELD_S3_BUCKET=claimshield-nexus-data-2026,S3_INPUT_PREFIX=incoming/,CLAIMSHIELD_ENVIRONMENT=hackathon}"
```

Or from a machine with AWS credentials and boto3:

```bash
cd infra/lambda/claimshield-s3-processor
python update_env.py
```

The API host must be reachable from Lambda. `http://127.0.0.1:8000` will not work. Production API: `https://claimshield-nexus-api.vercel.app`.
