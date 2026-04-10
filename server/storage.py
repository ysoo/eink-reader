"""
Thin wrapper around Azure Blob Storage.

All book .bin files and the todo_sync.txt live in one container.
The container name is read from the AZURE_STORAGE_CONTAINER env var
(default: "eink").

SAS URLs have a 1-hour validity — long enough for the Pico to download
even on a slow connection.
"""

import os
from datetime import datetime, timedelta, timezone

from azure.storage.blob import (
    BlobServiceClient,
    BlobSasPermissions,
    ContentSettings,
    generate_blob_sas,
)

_CONTAINER = os.environ.get("AZURE_STORAGE_CONTAINER", "eink")
_CONN_STR  = os.environ["AZURE_STORAGE_CONN_STR"]

_client = BlobServiceClient.from_connection_string(_CONN_STR)
_container = _client.get_container_client(_CONTAINER)

# Extract account key directly from the connection string — more reliable than
# _client.credential.account_key which may return decoded bytes in some SDK versions.
def _parse_account_key(conn_str: str) -> str:
    for part in conn_str.split(';'):
        if part.startswith('AccountKey='):
            return part[len('AccountKey='):]
    raise ValueError("AccountKey not found in connection string")

_ACCOUNT_KEY = _parse_account_key(_CONN_STR)


def _ensure_container():
    try:
        _container.create_container()
    except Exception:
        pass  # Already exists


def upload(name: str, data: bytes, content_type: str = "application/octet-stream") -> None:
    """Upload *data* as blob *name*, overwriting any existing blob."""
    _ensure_container()
    _container.upload_blob(name, data, overwrite=True,
                           content_settings=ContentSettings(content_type=content_type))


def download(name: str) -> bytes:
    """Return the full content of blob *name*."""
    return _container.download_blob(name).readall()


def delete(name: str) -> None:
    _container.delete_blob(name)


def list_books() -> list[str]:
    """Return blob names that look like book files (*.bin under books/)."""
    return [
        b.name
        for b in _container.list_blobs(name_starts_with="books/")
        if b.name.endswith(".bin")
    ]


def sas_url(name: str, valid_hours: int = 24) -> str:
    """Generate a short-lived SAS URL the Pico can download directly."""
    expiry = datetime.now(timezone.utc) + timedelta(hours=valid_hours)
    token = generate_blob_sas(
        account_name=_client.account_name,
        container_name=_CONTAINER,
        blob_name=name,
        account_key=_ACCOUNT_KEY,
        permission=BlobSasPermissions(read=True),
        expiry=expiry,
    )
    return f"https://{_client.account_name}.blob.core.windows.net/{_CONTAINER}/{name}?{token}"
