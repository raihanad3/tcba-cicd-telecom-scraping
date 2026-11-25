"""Skrip Continuous Deployment (CD): Mengunggah hasil ingestion raw, processed, dan metadata ke Azure Blob Storage."""

from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

from src.config import get_azure_settings


def upload_directory_results(out_dir: str | Path, account_name: str, container_name: str) -> list[str]:
    """Mengunggah berkas raw JSON, processed CSV/JSON, dan metadata run ke container Azure Blob privat."""
    root = Path(out_dir)
    account_url = f"https://{account_name}.blob.core.windows.net"
    credential = DefaultAzureCredential(exclude_managed_identity_credential=True)
    blob_service = BlobServiceClient(account_url=account_url, credential=credential)

    container_client = blob_service.get_container_client(container_name)
    if not container_client.exists():
        raise RuntimeError(
            f"Container '{container_name}' belum tersedia pada Storage Account '{account_name}'."
        )

    now_stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d_%H%M%S")
    upload_plan = [
        (root / "raw" / "tlkm_raw.json", f"raw/tlkm/tlkm_raw_{now_stamp}.json"),
        (root / "raw" / "isat_raw.json", f"raw/isat/isat_raw_{now_stamp}.json"),
        (root / "raw" / "excl_raw.json", f"raw/excl/excl_raw_{now_stamp}.json"),
        (root / "raw" / "macro_fx_raw.json", f"raw/macro/macro_fx_{now_stamp}.json"),
        (root / "processed" / "telecom_ingestion.csv", "processed/telecom_ingestion_latest.csv"),
        (root / "processed" / "telecom_ingestion.json", "processed/telecom_ingestion_latest.json"),
        (root / "processed" / "telecom_ingestion.csv", f"processed/history/telecom_ingestion_{now_stamp}.csv"),
        (root / "metadata" / "run_metadata.json", "metadata/run_metadata_latest.json"),
        (root / "metadata" / "run_metadata.json", f"metadata/history/run_metadata_{now_stamp}.json"),
    ]

    uploaded_blobs: list[str] = []
    for local_path, blob_name in upload_plan:
        if not local_path.is_file():
            raise FileNotFoundError(f"File artefak tidak ditemukan: {local_path}")
        blob_client = container_client.get_blob_client(blob_name)
        with local_path.open("rb") as data:
            blob_client.upload_blob(data, overwrite=True)
        uploaded_blobs.append(blob_name)
        print(f"[CD OK] Uploaded {local_path.as_posix()} -> https://{account_name}.blob.core.windows.net/{container_name}/{blob_name}")

    print("\n[CD VERIFY] Daftar blob terverifikasi di container:")
    for blob in container_client.list_blobs(name_starts_with="processed/"):
        print(f" - {blob.name} ({blob.size} bytes)")
    return uploaded_blobs


def main() -> None:
    defaults = get_azure_settings()
    parser = argparse.ArgumentParser(description="Upload ingested telecom data to Azure Blob Storage")
    parser.add_argument("--out-dir", default="data/live_out", help="Direktori output hasil pipeline")
    parser.add_argument("--account", default=defaults.storage_account, help="Nama Azure Storage Account")
    parser.add_argument("--container", default=defaults.storage_container, help="Nama Blob Container")
    args = parser.parse_args()

    upload_directory_results(out_dir=args.out_dir, account_name=args.account, container_name=args.container)


if __name__ == "__main__":
    main()
