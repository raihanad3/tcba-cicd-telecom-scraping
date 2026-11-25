"""Unit tests untuk penegakan data-contract pada DataFrame hasil transformasi."""

from pathlib import Path

import pytest

from src.ingest import load_fixture_payload
from src.transform import transform_payload
from src.validate import validate_dataframe


def test_validate_dataframe_accepts_valid_fixture() -> None:
    fixture = load_fixture_payload(Path("data/sample/sample_payload.json"))
    df, _ = transform_payload(fixture)
    validate_dataframe(df)


def test_validate_dataframe_rejects_negative_price() -> None:
    fixture = load_fixture_payload(Path("data/sample/sample_payload.json"))
    df, _ = transform_payload(fixture)
    df.loc[0, "market_price_idr"] = -100.0
    with pytest.raises(AssertionError):
        validate_dataframe(df)


def test_validate_dataframe_rejects_missing_emiten() -> None:
    fixture = load_fixture_payload(Path("data/sample/sample_payload.json"))
    df, _ = transform_payload(fixture)
    filtered = df[df["ticker"] != "EXCL"].copy()
    with pytest.raises(AssertionError):
        validate_dataframe(filtered)
