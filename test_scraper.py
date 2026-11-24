"""
Skrip Pengujian Continuous Integration (CI) untuk Pipeline Web Scraping Telekomunikasi.
Memastikan file CSV/JSON terbentuk, tidak kosong, skema kolom valid, dan nilai sentimen valid.
"""

from __future__ import annotations

import argparse
import json
import os
import pandas as pd

REQUIRED_COLUMNS = [
    "timestamp_utc",
    "news_id",
    "ticker",
    "emiten_name",
    "title",
    "source",
    "published_at",
    "sentiment_label",
    "sentiment_score",
    "url",
    "ingestion_channel",
]
VALID_TICKERS = {"TLKM", "ISAT", "EXCL"}
VALID_SENTIMENTS = {"positif", "netral", "negatif"}


def validate_output(out_dir: str) -> None:
    csv_path = os.path.join(out_dir, "telecom_news_scraped.csv")
    json_path = os.path.join(out_dir, "telecom_news_scraped.json")
    summary_path = os.path.join(out_dir, "scraping_summary.json")

    for path in (csv_path, json_path, summary_path):
        assert os.path.isfile(path), f"File output tidak ditemukan: {path}"
        assert os.path.getsize(path) > 0, f"File output kosong: {path}"

    df = pd.read_csv(csv_path)
    assert len(df) >= 3, f"Minimal 3 baris berita diharapkan, ditemukan: {len(df)}"
    for col in REQUIRED_COLUMNS:
        assert col in df.columns, f"Kolom wajib hilang: {col}"
        assert df[col].notna().all(), f"Terdapat nilai NULL pada kolom: {col}"

    assert set(df["ticker"]).issubset(VALID_TICKERS), f"Ticker tidak valid: {set(df['ticker'])}"
    assert set(df["sentiment_label"]).issubset(VALID_SENTIMENTS), f"Label sentimen tidak valid: {set(df['sentiment_label'])}"

    with open(json_path, "r", encoding="utf-8") as f:
        records = json.load(f)
    assert len(records) == len(df), "Jumlah record JSON tidak cocok dengan CSV"

    with open(summary_path, "r", encoding="utf-8") as f:
        summary = json.load(f)
    assert summary["total_articles"] == len(df), "Ringkasan jumlah artikel tidak sinkron"

    print(f"[CI PASS] Validasi sukses: {len(df)} artikel terverifikasi untuk ticker {sorted(df['ticker'].unique())}.")


def main() -> None:
    parser = argparse.ArgumentParser(description="CI Validation Test for Telecom Scraper")
    parser.add_argument("--out-dir", default="output", help="Direktori output hasil scraping")
    args = parser.parse_args()
    validate_output(args.out_dir)


if __name__ == "__main__":
    main()
