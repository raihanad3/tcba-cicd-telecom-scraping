"""
Skrip Continuous Deployment (CD): Mengunggah Hasil Web Scraping ke Azure Blob Storage
Menggunakan Microsoft Entra ID (DefaultAzureCredential / OIDC Federated Credentials).
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient


def upload_to_azure(out_dir: str, account_name: str, container_name: str) -> None:
    account_url = f"https://{account_name}.blob.core.windows.net"
    credential = DefaultAzureCredential(exclude_managed_identity_credential=True)
    blob_service = BlobServiceClient(account_url=account_url, credential=credential)

    container_client = blob_service.get_container_client(container_name)
    if not container_client.exists():
        container_client.create_container()

    now_stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d_%H%M%S")
    files_to_upload = [
        ("telecom_news_scraped.csv", "latest/telecom_news_scraped.csv"),
        ("telecom_news_scraped.json", "latest/telecom_news_scraped.json"),
        ("scraping_summary.json", "latest/scraping_summary.json"),
        ("telecom_news_scraped.csv", f"history/telecom_news_{now_stamp}.csv"),
    ]

    for local_name, blob_name in files_to_upload:
        local_path = os.path.join(out_dir, local_name)
        if not os.path.isfile(local_path):
            raise FileNotFoundError(f"File tidak ditemukan: {local_path}")
        blob_client = container_client.get_blob_client(blob_name)
        with open(local_path, "rb") as data:
            blob_client.upload_blob(data, overwrite=True)
        print(f"[CD OK] Uploaded {local_path} -> https://{account_name}.blob.core.windows.net/{container_name}/{blob_name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload scraping results to Azure Blob Storage")
    parser.add_argument("--out-dir", default="output")
    parser.add_argument("--account", default=os.getenv("AZURE_STORAGE_ACCOUNT", "sepatubola"))
    parser.add_argument("--container", default=os.getenv("AZURE_CONTAINER_NAME", "telecom-scraping"))
    args = parser.parse_args()
    upload_to_azure(args.out_dir, args.account, args.container)


if __name__ == "__main__":
    main()
