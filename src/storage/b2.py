"""Download small analytical marts from Backblaze B2's S3-compatible API."""

import os
from pathlib import Path


def configured() -> bool:
    return all(os.getenv(name) for name in ("B2_ENDPOINT", "B2_BUCKET", "B2_KEY_ID", "B2_APPLICATION_KEY"))


def ensure_mart(name: str, local_path: Path) -> Path:
    """Return a local mart path, downloading it from B2 when configured."""
    if local_path.exists() or not configured():
        return local_path

    import boto3

    local_path.parent.mkdir(parents=True, exist_ok=True)
    client = boto3.client(
        "s3",
        endpoint_url=os.environ["B2_ENDPOINT"],
        aws_access_key_id=os.environ["B2_KEY_ID"],
        aws_secret_access_key=os.environ["B2_APPLICATION_KEY"],
    )
    temporary_path = local_path.with_suffix(local_path.suffix + ".download")
    client.download_file(os.environ["B2_BUCKET"], f"marts/{name}", str(temporary_path))
    temporary_path.replace(local_path)
    return local_path
