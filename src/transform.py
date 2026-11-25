"""Modul transformasi & standardisasi skema berita, harga saham, kurs makro, dan skor sentimen."""

from __future__ import annotations

import datetime as dt
import hashlib
import re
from typing import Any

import pandas as pd

from src.config import (
    NEGATIVE_WORDS,
    POSITIVE_WORDS,
    REQUIRED_COLUMNS,
    SENTIMENT_NEGATIVE_THRESHOLD,
    SENTIMENT_POSITIVE_THRESHOLD,
)


def clean_title(title: str) -> str:
    """Membersihkan suffix nama media dan spasi berlebih dari judul berita."""
    cleaned = re.sub(r"\s+-\s+[^-]{2,60}$", "", title or "")
    return re.sub(r"\s+", " ", cleaned).strip()


def score_sentiment(
    text: str,
    pos_threshold: float = SENTIMENT_POSITIVE_THRESHOLD,
    neg_threshold: float = SENTIMENT_NEGATIVE_THRESHOLD,
) -> tuple[str, float]:
    """Menghitung skor (-1.0..1.0) dan label sentimen berbasis leksikon keuangan Indonesia."""
    low = (text or "").lower()
    pos_hits = sum(1 for word in POSITIVE_WORDS if word in low)
    neg_hits = sum(1 for word in NEGATIVE_WORDS if word in low)
    score = round(max(-1.0, min(1.0, 0.25 * (pos_hits - neg_hits))), 3)
    if score >= pos_threshold:
        return "positif", score
    if score <= neg_threshold:
        return "negatif", score
    return "netral", score


def compute_quarter_period(timestamp_utc: str) -> str:
    """Mengonversi timestamp ISO-8601 UTC menjadi label kuartal seperti 2026Q4."""
    parsed = dt.datetime.fromisoformat(timestamp_utc.replace("Z", "+00:00"))
    quarter_idx = (parsed.month - 1) // 3 + 1
    return f"{parsed.year}Q{quarter_idx}"


def transform_payload(raw_payload: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Mengubah payload mentah per-emiten dan makro FX menjadi DataFrame terstandar dan ringkasan."""
    ingested_at = str(raw_payload["ingested_at_utc"])
    quarter_label = compute_quarter_period(ingested_at)
    macro_fx = raw_payload.get("macro_fx") or {}
    usd_idr_rate = float(macro_fx["usd_idr_rate"])

    rows: list[dict[str, Any]] = []
    market_snapshots: list[dict[str, Any]] = []
    emitens_dict = raw_payload.get("emitens") or {}

    for ticker, block in emitens_dict.items():
        snapshot = block["market_snapshot"]
        market_snapshots.append(snapshot)
        market_price = float(snapshot["market_price_idr"])
        for art in block.get("articles", []):
            title = clean_title(str(art.get("raw_title") or art.get("title") or ""))
            if not title:
                continue
            label, score = score_sentiment(title)
            news_id = hashlib.sha1(f"{ticker}|{title.lower()}".encode("utf-8")).hexdigest()[:14]
            rows.append({
                "timestamp_utc": ingested_at,
                "quarter_period": quarter_label,
                "news_id": news_id,
                "ticker": ticker,
                "emiten_name": str(art.get("emiten_name") or block["emiten_name"]),
                "title": title,
                "source": str(art["source"]),
                "published_at": str(art["published_at"]),
                "sentiment_label": label,
                "sentiment_score": score,
                "market_price_idr": market_price,
                "usd_idr_rate": usd_idr_rate,
                "url": str(art["url"]),
                "ingestion_channel": str(art["ingestion_channel"]),
            })

    if not rows:
        df = pd.DataFrame(columns=REQUIRED_COLUMNS)
    else:
        df = pd.DataFrame(rows).drop_duplicates(subset=["news_id"]).reset_index(drop=True)
        df = df[REQUIRED_COLUMNS]

    mean_sent = (
        {k: round(float(v), 4) for k, v in df.groupby("ticker")["sentiment_score"].mean().items()}
        if not df.empty
        else {}
    )

    summary: dict[str, Any] = {
        "mode": str(raw_payload.get("mode", "unknown")),
        "ingested_at_utc": ingested_at,
        "quarter_period": quarter_label,
        "total_articles": int(len(df)),
        "per_ticker": df["ticker"].value_counts().to_dict() if not df.empty else {},
        "mean_sentiment_by_ticker": mean_sent,
        "sentiment_distribution": df["sentiment_label"].value_counts().to_dict() if not df.empty else {},
        "channels": df["ingestion_channel"].value_counts().to_dict() if not df.empty else {},
        "usd_idr_rate": usd_idr_rate,
        "macro_fx": macro_fx,
        "market_snapshots": market_snapshots,
    }
    return df, summary
