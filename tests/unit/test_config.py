"""Unit tests untuk konfigurasi domain emiten telekomunikasi dan parameter CI/CD."""

from src.config import (
    EMITENS,
    MAX_ARTICLES_PER_SOURCE,
    REQUIRED_COLUMNS,
    SENTIMENT_NEGATIVE_THRESHOLD,
    SENTIMENT_POSITIVE_THRESHOLD,
    VALID_TICKERS,
    get_azure_settings,
)


def test_emitens_match_final_project_theme() -> None:
    tickers = {str(item["ticker"]) for item in EMITENS}
    assert tickers == VALID_TICKERS
    assert len(EMITENS) == 3
    for item in EMITENS:
        assert str(item["yahoo_symbol"]).endswith(".JK")
        assert float(item["fallback_price_idr"]) > 0


def test_domain_limits_and_thresholds() -> None:
    assert MAX_ARTICLES_PER_SOURCE == 10
    assert SENTIMENT_POSITIVE_THRESHOLD == 0.20
    assert SENTIMENT_NEGATIVE_THRESHOLD == -0.20


def test_required_columns_cover_market_macro_and_sentiment() -> None:
    for col in ("ticker", "sentiment_label", "sentiment_score", "market_price_idr", "usd_idr_rate"):
        assert col in REQUIRED_COLUMNS


def test_azure_settings_env_override(monkeypatch) -> None:
    monkeypatch.setenv("AZURE_STORAGE_ACCOUNT", "stcustomtest")
    monkeypatch.setenv("AZURE_STORAGE_CONTAINER", "custom-container")
    cfg = get_azure_settings()
    assert cfg.storage_account == "stcustomtest"
    assert cfg.storage_container == "custom-container"
