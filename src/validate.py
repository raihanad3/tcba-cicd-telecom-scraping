"""Modul validasi data-contract untuk DataFrame hasil transformasi dan artefak output pipeline."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.config import REQUIRED_COLUMNS, VALID_SENTIMENTS, VALID_TICKERS


def validate_dataframe(df: pd.DataFrame) -> None:
    """Memvalidasi integritas skema, tipe nilai, cakupan emiten, dan keunikan berita."""
    assert len(df) >= 3, f"Minimal 3 artikel diharapkan, ditemukan: {len(df)}"
    for col in REQUIRED_COLUMNS:
        assert col in df.columns, f"Kolom wajib hilang: {col}"
        assert df[col].notna().all(), f"Terdapat nilai NULL pada kolom: {col}"

    assert df["news_id"].is_unique, "Ditemukan duplikasi news_id setelah transformasi"

    observed_tickers = set(df["ticker"].astype(str))
    assert observed_tickers.issubset(VALID_TICKERS), f"Ticker tidak dikenal: {observed_tickers}"
    assert observed_tickers == VALID_TICKERS, (
        f"Semua emiten {sorted(VALID_TICKERS)} wajib terwakili, ditemukan: {sorted(observed_tickers)}"
    )

    observed_sentiments = set(df["sentiment_label"].astype(str))
    assert observed_sentiments.issubset(VALID_SENTIMENTS), f"Label sentimen tidak valid: {observed_sentiments}"

    scores = df["sentiment_score"].astype(float)
    assert ((scores >= -1.0) & (scores <= 1.0)).all(), "Skor sentimen harus berada di rentang [-1.0, 1.0]"

    prices = df["market_price_idr"].astype(float)
    assert (prices > 0).all(), "Harga saham market_price_idr harus bernilai positif"

    fx_rates = df["usd_idr_rate"].astype(float)
    assert (fx_rates > 0).all(), "Kurs makro usd_idr_rate harus bernilai positif"


def validate_output_files(out_dir: str | Path) -> None:
    """Memastikan seluruh berkas raw JSON, processed CSV/JSON, dan metadata konsisten."""
    root = Path(out_dir)
    expected_files = [
        root / "raw" / "tlkm_raw.json",
        root / "raw" / "isat_raw.json",
        root / "raw" / "excl_raw.json",
        root / "raw" / "macro_fx_raw.json",
        root / "processed" / "telecom_ingestion.csv",
        root / "processed" / "telecom_ingestion.json",
        root / "metadata" / "run_metadata.json",
    ]
    for file_path in expected_files:
        assert file_path.is_file(), f"Berkas output wajib tidak ditemukan: {file_path}"
        assert file_path.stat().st_size > 0, f"Berkas output kosong: {file_path}"

    df = pd.read_csv(root / "processed" / "telecom_ingestion.csv")
    validate_dataframe(df)

    with (root / "processed" / "telecom_ingestion.json").open("r", encoding="utf-8") as fh:
        records = json.load(fh)
    assert len(records) == len(df), "Jumlah record JSON tidak sinkron dengan CSV"

    with (root / "metadata" / "run_metadata.json").open("r", encoding="utf-8") as fh:
        metadata = json.load(fh)
    assert metadata["total_articles"] == len(df), "Field total_articles metadata tidak sinkron"
    assert "quarter_period" in metadata, "Field quarter_period wajib ada di metadata"
    assert "mean_sentiment_by_ticker" in metadata, "Field mean_sentiment_by_ticker wajib ada di metadata"
