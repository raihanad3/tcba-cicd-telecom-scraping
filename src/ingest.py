"""Modul ingestion data berita industri, pasar saham (Yahoo Finance), dan makro USD/IDR (Frankfurter)."""

from __future__ import annotations

import datetime as dt
import json
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

from src.config import (
    DEFAULT_FALLBACK_USD_IDR,
    EMITENS,
    HEADERS,
    MAX_ARTICLES_PER_SOURCE,
)


def fetch_google_news_rss(emiten: dict[str, Any], limit: int = MAX_ARTICLES_PER_SOURCE) -> list[dict[str, Any]]:
    """Mengambil berita emiten telekomunikasi dari feed RSS Google News."""
    ticker = str(emiten["ticker"])
    q = urllib.parse.quote_plus(str(emiten["query"]))
    url = f"https://news.google.com/rss/search?q={q}&hl=id&gl=ID&ceid=ID:id"
    records: list[dict[str, Any]] = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        for item in root.findall(".//item")[:limit]:
            raw_title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            pub_date = (item.findtext("pubDate") or "").strip()
            source_el = item.find("source")
            source_name = source_el.text.strip() if source_el is not None and source_el.text else "Google News RSS"
            if not raw_title or not link:
                continue
            records.append({
                "ticker": ticker,
                "emiten_name": str(emiten["name"]),
                "raw_title": raw_title,
                "source": source_name,
                "published_at": pub_date,
                "url": link,
                "ingestion_channel": "google_news_rss",
            })
    except Exception as exc:
        print(f"[WARN] Google News RSS gagal untuk {ticker}: {exc}")
    return records


def fetch_cnbc_tag_bs4(emiten: dict[str, Any], limit: int = MAX_ARTICLES_PER_SOURCE) -> list[dict[str, Any]]:
    """Scraping halaman tag CNBC Indonesia menggunakan BeautifulSoup4."""
    ticker = str(emiten["ticker"])
    records: list[dict[str, Any]] = []
    try:
        resp = requests.get(str(emiten["cnbc_tag"]), headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        for a_tag in soup.select("article a"):
            href = (a_tag.get("href") or "").strip()
            h_el = a_tag.select_one("h2, h3")
            title_raw = h_el.get_text(" ", strip=True) if h_el else a_tag.get_text(" ", strip=True)
            if len(title_raw) < 20 or not href.startswith("http"):
                continue
            records.append({
                "ticker": ticker,
                "emiten_name": str(emiten["name"]),
                "raw_title": title_raw,
                "source": "CNBC Indonesia",
                "published_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                "url": href,
                "ingestion_channel": "cnbc_beautifulsoup",
            })
            if len(records) >= limit:
                break
    except Exception as exc:
        print(f"[WARN] CNBC Tag BS4 dilewati untuk {ticker}: {exc}")
    return records


def fetch_kontan_search_bs4(emiten: dict[str, Any], limit: int = MAX_ARTICLES_PER_SOURCE) -> list[dict[str, Any]]:
    """Scraping halaman pencarian Kontan.co.id menggunakan BeautifulSoup4."""
    ticker = str(emiten["ticker"])
    records: list[dict[str, Any]] = []
    search_url = f"https://www.kontan.co.id/search/?search={urllib.parse.quote(ticker)}"
    try:
        resp = requests.get(search_url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        for item in soup.select(".list-berita li h1 a, .list-berita li h2 a, .ket a"):
            href = (item.get("href") or "").strip()
            title_raw = item.get_text(" ", strip=True)
            if len(title_raw) < 20 or not href.startswith("http"):
                continue
            records.append({
                "ticker": ticker,
                "emiten_name": str(emiten["name"]),
                "raw_title": title_raw,
                "source": "Kontan",
                "published_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                "url": href,
                "ingestion_channel": "kontan_beautifulsoup",
            })
            if len(records) >= limit:
                break
    except Exception as exc:
        print(f"[WARN] Kontan Search BS4 dilewati untuk {ticker}: {exc}")
    return records


def fetch_yahoo_market_snapshot(emiten: dict[str, Any]) -> dict[str, Any]:
    """Mengambil harga penutupan terbaru dari Yahoo Finance Chart API."""
    ticker = str(emiten["ticker"])
    symbol = str(emiten["yahoo_symbol"])
    fallback_px = float(emiten["fallback_price_idr"])
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}?range=5d&interval=1d"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=12)
        resp.raise_for_status()
        result = resp.json()["chart"]["result"][0]
        meta = result["meta"]
        close_px = meta.get("regularMarketPrice")
        prev_px = meta.get("chartPreviousClose")
        if close_px is None or float(close_px) <= 0:
            raise ValueError("Harga pasar tidak valid")
        close_f = round(float(close_px), 2)
        prev_f = round(float(prev_px), 2) if prev_px else close_f
        chg_pct = round(((close_f - prev_f) / prev_f) * 100, 2) if prev_f else 0.0
        return {
            "ticker": ticker,
            "symbol": symbol,
            "market_price_idr": close_f,
            "prev_close_idr": prev_f,
            "change_5d_pct": chg_pct,
            "currency": str(meta.get("currency", "IDR")),
            "source_status": "live_yahoo",
        }
    except Exception as exc:
        print(f"[WARN] Yahoo snapshot gagal untuk {symbol}, gunakan fallback referensi: {exc}")
        return {
            "ticker": ticker,
            "symbol": symbol,
            "market_price_idr": fallback_px,
            "prev_close_idr": fallback_px,
            "change_5d_pct": 0.0,
            "currency": "IDR",
            "source_status": "fallback_reference",
        }


def fetch_frankfurter_usd_idr() -> dict[str, Any]:
    """Mengambil kurs makroekonomi USD/IDR terbaru dari Frankfurter API (data ECB)."""
    endpoints = (
        "https://api.frankfurter.app/latest?from=USD&to=IDR",
        "https://api.frankfurter.dev/v1/latest?from=USD&to=IDR",
    )
    for url in endpoints:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=12)
            resp.raise_for_status()
            data = resp.json()
            rate = float((data.get("rates") or {})["IDR"])
            if rate <= 0:
                raise ValueError("Kurs USD/IDR tidak valid")
            return {
                "base": "USD",
                "target": "IDR",
                "usd_idr_rate": round(rate, 2),
                "as_of_date": str(data.get("date", dt.date.today().isoformat())),
                "source": "Frankfurter ECB API",
                "source_status": "live_frankfurter",
            }
        except Exception as exc:
            print(f"[WARN] Frankfurter endpoint {url} gagal: {exc}")
    return {
        "base": "USD",
        "target": "IDR",
        "usd_idr_rate": DEFAULT_FALLBACK_USD_IDR,
        "as_of_date": dt.date.today().isoformat(),
        "source": "Fallback Macro Reference",
        "source_status": "fallback_reference",
    }


def _fallback_news_for_emiten(emiten: dict[str, Any], now_iso: str) -> list[dict[str, Any]]:
    """Fallback berita deterministik per emiten bila sumber berita diblokir jaringan."""
    ticker = str(emiten["ticker"])
    templates = {
        "TLKM": ("Telkom perluas kapasitas Data Center NeutraDC dan ekspansi jaringan 5G guna dorong laba", "CNBC Indonesia", "https://www.cnbcindonesia.com/market"),
        "ISAT": ("Indosat Ooredoo Hutchison catat pertumbuhan pendapatan data seluler dan efisiensi beban operasional", "Kontan", "https://investasi.kontan.co.id"),
        "EXCL": ("Pasca integrasi XLSMART, beban capex jaringan meningkat di tengah kompetisi tarif data", "Bisnis Indonesia", "https://market.bisnis.com"),
    }
    title, source, url = templates[ticker]
    return [{
        "ticker": ticker,
        "emiten_name": str(emiten["name"]),
        "raw_title": title,
        "source": source,
        "published_at": now_iso,
        "url": url,
        "ingestion_channel": "deterministic_fallback",
    }]


def ingest_live_payload(limit_per_source: int = MAX_ARTICLES_PER_SOURCE) -> dict[str, Any]:
    """Menjalankan ingestion live untuk seluruh emiten telekomunikasi dan kurs makro USD/IDR."""
    now_utc = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    now_iso = now_utc.isoformat()
    macro_fx = fetch_frankfurter_usd_idr()

    emiten_payloads: dict[str, dict[str, Any]] = {}
    for emiten in EMITENS:
        ticker = str(emiten["ticker"])
        articles: list[dict[str, Any]] = []
        articles.extend(fetch_google_news_rss(emiten, limit=limit_per_source))
        articles.extend(fetch_cnbc_tag_bs4(emiten, limit=max(2, limit_per_source - 2)))
        articles.extend(fetch_kontan_search_bs4(emiten, limit=max(2, limit_per_source - 3)))
        if not articles:
            articles = _fallback_news_for_emiten(emiten, now_iso)
        market = fetch_yahoo_market_snapshot(emiten)
        emiten_payloads[ticker] = {
            "ticker": ticker,
            "emiten_name": str(emiten["name"]),
            "market_snapshot": market,
            "articles": articles,
        }

    return {
        "mode": "live",
        "ingested_at_utc": now_iso,
        "macro_fx": macro_fx,
        "emitens": emiten_payloads,
    }


def load_fixture_payload(fixture_path: str | Path) -> dict[str, Any]:
    """Memuat payload fixture deterministik untuk pengujian CI lokal dan GitHub Actions."""
    path = Path(fixture_path)
    with path.open("r", encoding="utf-8") as fh:
        payload = json.load(fh)
    payload.setdefault("mode", "fixture")
    return payload
