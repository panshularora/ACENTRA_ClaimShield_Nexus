"""Object store for S3 ingest. Local directory is used in tests and AWS-free development."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from claimshield.core.config import Settings
from claimshield.core.errors import NotFound, ServiceUnavailable, ValidationFailed


@dataclass(frozen=True)
class StoredObject:
    key: str
    body: bytes
    etag: str


class ObjectStore(Protocol):
    def get(self, bucket: str, key: str) -> StoredObject: ...

    def list_csv(self, bucket: str, prefix: str) -> list[tuple[str, str]]: ...

    def put(self, bucket: str, key: str, body: bytes, content_type: str) -> None: ...


class LocalDirStore:
    """Maps s3://bucket/key to {root}/{key} so ingest works without AWS."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def get(self, bucket: str, key: str) -> StoredObject:
        path = self._path(key)
        if not path.is_file():
            raise NotFound("s3 object not found")
        body = path.read_bytes()
        return StoredObject(key=key, body=body, etag=_etag(body))

    def list_csv(self, bucket: str, prefix: str) -> list[tuple[str, str]]:
        folder = self._path(prefix)
        if not folder.is_dir():
            return []
        out: list[tuple[str, str]] = []
        for path in sorted(folder.iterdir()):
            if not path.is_file() or path.suffix.lower() != ".csv":
                continue
            key = f"{prefix.rstrip('/')}/{path.name}" if prefix else path.name
            out.append((key, _etag(path.read_bytes())))
        return out

    def put(self, bucket: str, key: str, body: bytes, content_type: str) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)

    def _path(self, key: str) -> Path:
        return self.root / key


class S3Store:
    def __init__(self, *, region: str) -> None:
        try:
            import boto3
        except ImportError as exc:  # pragma: no cover
            raise ServiceUnavailable("s3 client is not installed") from exc
        self._client = boto3.client("s3", region_name=region)

    def get(self, bucket: str, key: str) -> StoredObject:
        try:
            response = self._client.get_object(Bucket=bucket, Key=key)
        except Exception as exc:
            raise NotFound("s3 object not found") from exc
        body = response["Body"].read()
        etag = str(response.get("ETag") or _etag(body)).strip('"')
        return StoredObject(key=key, body=body, etag=etag)

    def list_csv(self, bucket: str, prefix: str) -> list[tuple[str, str]]:
        try:
            paginator = self._client.get_paginator("list_objects_v2")
            out: list[tuple[str, str]] = []
            for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
                for item in page.get("Contents") or []:
                    key = str(item["Key"])
                    if key.endswith("/") or not key.lower().endswith(".csv"):
                        continue
                    if "/" in key[len(prefix) :]:
                        continue
                    etag = str(item.get("ETag") or "").strip('"')
                    out.append((key, etag))
            return out
        except Exception as exc:
            raise ServiceUnavailable("s3 list failed") from exc

    def put(self, bucket: str, key: str, body: bytes, content_type: str) -> None:
        self._client.put_object(
            Bucket=bucket,
            Key=key,
            Body=body,
            ContentType=content_type,
        )


def build_store(settings: Settings) -> ObjectStore:
    if settings.s3_local_dir is not None:
        return LocalDirStore(Path(settings.s3_local_dir))
    return S3Store(region=settings.aws_region)


def assert_safe_key(key: str, *, incoming_prefix: str) -> None:
    normalized = key.replace("\\", "/")
    if normalized != key or ".." in normalized.split("/"):
        raise ValidationFailed("invalid object key")
    prefix = incoming_prefix if incoming_prefix.endswith("/") else incoming_prefix + "/"
    if not normalized.startswith(prefix):
        raise ValidationFailed("object is outside incoming prefix")
    if not normalized.lower().endswith(".csv"):
        raise ValidationFailed("object is not a csv")


def _etag(body: bytes) -> str:
    return hashlib.md5(body, usedforsecurity=False).hexdigest()
