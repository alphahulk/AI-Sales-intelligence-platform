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
    from botocore.config import Config

    endpoint = os.environ["B2_ENDPOINT"].strip()
    region = endpoint.split("s3.", 1)[-1].split(".", 1)[0] if "s3." in endpoint else "us-east-005"
    local_path.parent.mkdir(parents=True, exist_ok=True)
    client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        region_name=region,
        aws_access_key_id=os.environ["B2_KEY_ID"].strip(),
        aws_secret_access_key=os.environ["B2_APPLICATION_KEY"].strip(),
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )
    temporary_path = local_path.with_suffix(local_path.suffix + ".download")
    client.download_file(os.environ["B2_BUCKET"], f"marts/{name}", str(temporary_path))
    temporary_path.replace(local_path)
    return local_path
