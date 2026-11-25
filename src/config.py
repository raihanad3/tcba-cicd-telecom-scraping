"""Konfigurasi terpusat untuk pipeline ingestion data profitabilitas telekomunikasi (TLKM, ISAT, EXCL)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Final

# Konstanta domain yang menjadi single source of truth bagi ingestion dan transformasi
MAX_ARTICLES_PER_SOURCE = 6
SENTIMENT_POSITIVE_THRESHOLD = 0.20
SENTIMENT_NEGATIVE_THRESHOLD = -0.20
DEFAULT_FALLBACK_USD_IDR = 15850.0

VALID_TICKERS: Final[set[str]] = {"TLKM", "ISAT", "EXCL"}
VALID_SENTIMENTS: Final[set[str]] = {"positif", "netral", "negatif"}

REQUIRED_COLUMNS: Final[list[str]] = [
    "timestamp_utc",
    "quarter_period",
    "news_id",
    "ticker",
    "emiten_name",
    "title",
    "source",
    "published_at",
    "sentiment_label",
    "sentiment_score",
    "market_price_idr",
    "usd_idr_rate",
    "url",
    "ingestion_channel",
]

HEADERS: Final[dict[str, str]] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
}

EMITENS: Final[list[dict[str, object]]] = [
    {
        "ticker": "TLKM",
        "name": "PT Telkom Indonesia (Persero) Tbk",
        "yahoo_symbol": "TLKM.JK",
        "query": "saham TLKM OR Telkom Indonesia laba",
        "cnbc_tag": "https://www.cnbcindonesia.com/tag/tlkm",
        "fallback_price_idr": 2750.0,
    },
    {
        "ticker": "ISAT",
        "name": "PT Indosat Tbk",
        "yahoo_symbol": "ISAT.JK",
        "query": "saham ISAT OR Indosat Ooredoo Hutchison laba",
        "cnbc_tag": "https://www.cnbcindonesia.com/tag/indosat",
        "fallback_price_idr": 2400.0,
    },
    {
        "ticker": "EXCL",
        "name": "PT XLSMART Telecom Sejahtera Tbk",
        "yahoo_symbol": "EXCL.JK",
        "query": "saham EXCL OR XL Axiata OR XLSMART laba",
        "cnbc_tag": "https://www.cnbcindonesia.com/tag/xl-axiata",
        "fallback_price_idr": 2250.0,
    },
]

EMITEN_BY_TICKER: Final[dict[str, dict[str, object]]] = {
    str(item["ticker"]): item for item in EMITENS
}

POSITIVE_WORDS: Final[set[str]] = {
    "naik", "tumbuh", "laba", "untung", "positif", "menguat", "rekor", "dividen",
    "ekspansi", "solid", "surplus", "merger", "5g", "ai", "data center", "efisiensi",
    "kolaborasi", "katalis", "prospek", "capex", "investasi", "melonjak", "cuan",
}

NEGATIVE_WORDS: Final[set[str]] = {
    "turun", "rugi", "koreksi", "melemah", "anjlok", "tekanan", "utang", "beban",
    "perang tarif", "kompetisi", "sanksi", "gagal", "susut", "penurunan", "defisit",
    "phk", "gugatan", "gangguan", "negatif", "denda", "pangkas", "tertekan",
}


@dataclass(frozen=True)
class AzureSettings:
    """Konfigurasi Azure Storage dari environment variables tanpa menyimpan kredensial."""

    storage_account: str
    storage_container: str


def get_azure_settings() -> AzureSettings:
    """Membaca konfigurasi Azure Blob Storage dari environment variables."""
    return AzureSettings(
        storage_account=os.getenv("AZURE_STORAGE_ACCOUNT", "sttcba09cicd"),
        storage_container=os.getenv("AZURE_STORAGE_CONTAINER", "telecom-cicd-data"),
    )
