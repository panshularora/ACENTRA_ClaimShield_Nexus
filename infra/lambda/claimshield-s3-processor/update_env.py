"""Push Lambda env for claimshield-s3-processor. Does not print the token.

Requires AWS credentials in the default chain (env, shared config, or instance role).
Never commit CLAIMSHIELD_INTERNAL_TOKEN.
"""

from __future__ import annotations

import os
import sys
import zipfile
from io import BytesIO
from pathlib import Path

FUNCTION = os.environ.get("LAMBDA_FUNCTION", "claimshield-s3-processor")
REGION = os.environ.get("AWS_REGION", "ap-south-1")
API_URL = os.environ.get("CLAIMSHIELD_API_URL", "https://claimshield-nexus-api.vercel.app")
BUCKET = os.environ.get("S3_BUCKET", os.environ.get("CLAIMSHIELD_S3_BUCKET", "claimshield-nexus-data-2026"))
INCOMING = os.environ.get("S3_INPUT_PREFIX", os.environ.get("CLAIMSHIELD_S3_INCOMING_PREFIX", "incoming/"))
TOKEN = os.environ.get("CLAIMSHIELD_INTERNAL_TOKEN", "")
HANDLER = Path(__file__).with_name("handler.py")


def main() -> int:
    if not TOKEN:
        print("CLAIMSHIELD_INTERNAL_TOKEN is required in the environment", file=sys.stderr)
        return 2
    try:
        import boto3
    except ImportError:
        print("boto3 is required: pip install boto3", file=sys.stderr)
        return 2

    client = boto3.client("lambda", region_name=REGION)
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.write(HANDLER, arcname="handler.py")
    client.update_function_code(FunctionName=FUNCTION, ZipFile=buf.getvalue())
    waiter = client.get_waiter("function_updated")
    waiter.wait(FunctionName=FUNCTION)
    client.update_function_configuration(
        FunctionName=FUNCTION,
        Timeout=120,
        MemorySize=256,
        Environment={
            "Variables": {
                "CLAIMSHIELD_API_URL": API_URL.rstrip("/"),
                "CLAIMSHIELD_INTERNAL_TOKEN": TOKEN,
                "CLAIMSHIELD_S3_BUCKET": BUCKET,
                "S3_BUCKET": BUCKET,
                "CLAIMSHIELD_S3_INCOMING_PREFIX": INCOMING,
                "S3_INPUT_PREFIX": INCOMING,
                "CLAIMSHIELD_ENVIRONMENT": os.environ.get("CLAIMSHIELD_ENVIRONMENT", "hackathon"),
            }
        },
    )
    print(f"updated {FUNCTION} in {REGION} api={API_URL} bucket={BUCKET} prefix={INCOMING}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
