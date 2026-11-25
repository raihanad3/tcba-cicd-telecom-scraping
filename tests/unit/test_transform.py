"""Unit tests untuk pembersihan judul, skor sentimen leksikon, dan transformasi payload."""

from pathlib import Path

from src.ingest import load_fixture_payload
from src.transform import clean_title, compute_quarter_period, score_sentiment, transform_payload


def test_clean_title_strips_trailing_media_suffix() -> None:
    raw = "Laba Telkom Menguat di Kuartal III   - CNBC Indonesia"
    assert clean_title(raw) == "Laba Telkom Menguat di Kuartal III"


def test_score_sentiment_classification() -> None:
    pos_label, pos_score = score_sentiment("Laba bersih tumbuh solid berkat ekspansi 5G dan data center")
    neg_label, neg_score = score_sentiment("Beban utang dan perang tarif picu tekanan serta koreksi")
    neu_label, neu_score = score_sentiment("Rapat umum pemegang saham tahunan digelar hari ini")

    assert pos_label == "positif" and pos_score > 0
    assert neg_label == "negatif" and neg_score < 0
    assert neu_label == "netral" and neu_score == 0.0


def test_compute_quarter_period() -> None:
    assert compute_quarter_period("2026-11-25T00:00:00+00:00") == "2026Q4"
    assert compute_quarter_period("2026-02-14T12:00:00Z") == "2026Q1"


def test_transform_payload_from_fixture() -> None:
    fixture = load_fixture_payload(Path("data/sample/sample_payload.json"))
    df, summary = transform_payload(fixture)

    assert len(df) == 4
    assert summary["quarter_period"] == "2026Q4"
    assert summary["usd_idr_rate"] == 15890.5
    assert set(df["ticker"]) == {"TLKM", "ISAT", "EXCL"}
    assert df["news_id"].is_unique
