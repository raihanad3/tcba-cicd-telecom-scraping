"""
Web Scraping Berita Industri & Data Pasar Emiten Telekomunikasi Indonesia (TLKM, ISAT, EXCL)
Sesuai Tema Final Project TCBA:
"Prediksi Arah Fluktuasi Angka Rasio Profitabilitas Perusahaan Sektor Jaringan
Telekomunikasi Indonesia (TLKM, ISAT, EXCL) Berbasis Cloud Azure melalui
Integrasi Data Pasar Keuangan, Makroekonomi, dan Sentimen Berita Industri."

Author : Raihan Ade Alfattah (L0224009) - Kelas A
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Any

import pandas as pd
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
}

EMITENS = {
    "TLKM": {
        "name": "PT Telkom Indonesia (Persero) Tbk",
        "yahoo_symbol": "TLKM.JK",
        "query": "saham TLKM OR Telkom Indonesia laba",
        "cnbc_tag": "https://www.cnbcindonesia.com/tag/tlkm",
    },
    "ISAT": {
        "name": "PT Indosat Tbk",
        "yahoo_symbol": "ISAT.JK",
        "query": "saham ISAT OR Indosat Ooredoo Hutchison laba",
        "cnbc_tag": "https://www.cnbcindonesia.com/tag/indosat",
    },
    "EXCL": {
        "name": "PT XLSMART Telecom Sejahtera Tbk",
        "yahoo_symbol": "EXCL.JK",
        "query": "saham EXCL OR XL Axiata OR XLSMART laba",
        "cnbc_tag": "https://www.cnbcindonesia.com/tag/xl-axiata",
    },
}

POSITIVE_WORDS = {
    "naik", "tumbuh", "laba", "untung", "positif", "menguat", "rekor", "dividen",
    "ekspansi", "solid", "surplus", "merger", "5g", "ai", "data center", "efisiensi",
    "kolaborasi", "katalis", "prospek", "capex", "investasi", "melonjak", "cuan",
}

NEGATIVE_WORDS = {
    "turun", "rugi", "koreksi", "melemah", "anjlok", "tekanan", "utang", "beban",
    "perang tarif", "kompetisi", "sanksi", "gagal", "susut", "penurunan", "defisit",
    "phk", "gugatan", "gangguan", "negatif", "denda", "pangkas", "tertekan",
}


def score_sentiment(text: str) -> tuple[str, float]:
    """Menghitung skor dan label sentimen berbasis leksikon keuangan Indonesia."""
    low = (text or "").lower()
    pos_hits = sum(1 for w in POSITIVE_WORDS if w in low)
    neg_hits = sum(1 for w in NEGATIVE_WORDS if w in low)
    raw = pos_hits - neg_hits
    if raw > 0:
        return "positif", round(min(1.0, 0.25 * raw), 3)
    if raw < 0:
        return "negatif", round(max(-1.0, 0.25 * raw), 3)
    return "netral", 0.0


def clean_title(title: str) -> str:
    """Membersihkan suffix nama media dan spasi berlebih dari judul berita."""
    cleaned = re.sub(r"\s+-\s+[^-]{2,60}$", "", title or "")
    return re.sub(r"\s+", " ", cleaned).strip()


def fetch_google_news_rss(ticker: str, meta: dict[str, str], limit: int = 8) -> list[dict[str, Any]]:
    """Scraping feed RSS Google News berbahasa Indonesia untuk emiten telekomunikasi."""
    q = urllib.parse.quote_plus(meta["query"])
    url = f"https://news.google.com/rss/search?q={q}&hl=id&gl=ID&ceid=ID:id"
    records: list[dict[str, Any]] = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        for item in root.findall(".//item")[:limit]:
            raw_title = item.findtext("title", default="").strip()
            link = item.findtext("link", default="").strip()
            pub_date = item.findtext("pubDate", default="").strip()
            source_el = item.find("source")
            source_name = source_el.text.strip() if source_el is not None and source_el.text else "Google News RSS"
            title = clean_title(raw_title)
            if not title:
                continue
            label, score = score_sentiment(title)
            records.append({
                "news_id": hashlib.sha1(f"{ticker}|{title.lower()}".encode()).hexdigest()[:14],
                "ticker": ticker,
                "emiten_name": meta["name"],
                "title": title,
                "source": source_name,
                "published_at": pub_date,
                "sentiment_label": label,
                "sentiment_score": score,
                "url": link,
                "ingestion_channel": "google_news_rss",
            })
    except Exception as exc:
        print(f"[WARN] Google News RSS gagal untuk {ticker}: {exc}")
    return records


def fetch_cnbc_tag_bs4(ticker: str, meta: dict[str, str], limit: int = 5) -> list[dict[str, Any]]:
    """Scraping halaman tag CNBC Indonesia menggunakan BeautifulSoup4."""
    records: list[dict[str, Any]] = []
    try:
        resp = requests.get(meta["cnbc_tag"], headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        for a_tag in soup.select("article a"):
            href = (a_tag.get("href") or "").strip()
            h_el = a_tag.select_one("h2, h3")
            title_raw = h_el.get_text(" ", strip=True) if h_el else a_tag.get_text(" ", strip=True)
            title = clean_title(title_raw)
            if len(title) < 20 or not href.startswith("http"):
                continue
            label, score = score_sentiment(title)
            records.append({
                "news_id": hashlib.sha1(f"{ticker}|{title.lower()}".encode()).hexdigest()[:14],
                "ticker": ticker,
                "emiten_name": meta["name"],
                "title": title,
                "source": "CNBC Indonesia",
                "published_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                "sentiment_label": label,
                "sentiment_score": score,
                "url": href,
                "ingestion_channel": "cnbc_beautifulsoup",
            })
            if len(records) >= limit:
                break
    except Exception as exc:
        print(f"[WARN] CNBC Tag BS4 dilewati untuk {ticker}: {exc}")
    return records


def fetch_yahoo_market_snapshot(ticker: str, symbol: str) -> dict[str, Any]:
    """Mengambil ringkasan harga penutupan terbaru dari Yahoo Finance Chart API."""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}?range=5d&interval=1d"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=12)
        resp.raise_for_status()
        result = resp.json()["chart"]["result"][0]
        meta = result["meta"]
        close_px = meta.get("regularMarketPrice")
        prev_px = meta.get("chartPreviousClose")
        chg_pct = round(((close_px - prev_px) / prev_px) * 100, 2) if close_px and prev_px else 0.0
        return {
            "ticker": ticker,
            "symbol": symbol,
            "market_price_idr": close_px,
            "change_5d_pct": chg_pct,
            "currency": meta.get("currency", "IDR"),
        }
    except Exception as exc:
        print(f"[WARN] Yahoo snapshot gagal untuk {symbol}: {exc}")
        return {"ticker": ticker, "symbol": symbol, "market_price_idr": None, "change_5d_pct": None, "currency": "IDR"}


def fallback_records(now_iso: str) -> list[dict[str, Any]]:
    """Fallback deterministik bila runner dibatasi firewall jaringan eksternal."""
    samples = [
        ("TLKM", "PT Telkom Indonesia (Persero) Tbk", "Telkom perluas kapasitas Data Center NeutraDC dan ekspansi jaringan 5G guna dorong laba", "CNBC Indonesia", "https://www.cnbcindonesia.com/market"),
        ("ISAT", "PT Indosat Tbk", "Indosat Ooredoo Hutchison catat pertumbuhan pendapatan data seluler dan efisiensi beban operasional", "Kontan", "https://investasi.kontan.co.id"),
        ("EXCL", "PT XLSMART Telecom Sejahtera Tbk", "Pasca integrasi XLSMART, beban capex jaringan meningkat di tengah kompetisi tarif data", "Bisnis Indonesia", "https://market.bisnis.com"),
    ]
    out = []
    for ticker, name, title, source, url in samples:
        label, score = score_sentiment(title)
        out.append({
            "news_id": hashlib.sha1(f"{ticker}|{title.lower()}".encode()).hexdigest()[:14],
            "ticker": ticker,
            "emiten_name": name,
            "title": title,
            "source": source,
            "published_at": now_iso,
            "sentiment_label": label,
            "sentiment_score": score,
            "url": url,
            "ingestion_channel": "deterministic_fallback",
        })
    return out


def run_scraping(out_dir: str) -> dict[str, Any]:
    """Menjalankan pipeline scraping multi-emiten dan menulis output ke CSV & JSON."""
    os.makedirs(out_dir, exist_ok=True)
    now_utc = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    now_iso = now_utc.isoformat()

    all_news: list[dict[str, Any]] = []
    market_snapshots: list[dict[str, Any]] = []

    for ticker, meta in EMITENS.items():
        rss_rows = fetch_google_news_rss(ticker, meta, limit=6)
        cnbc_rows = fetch_cnbc_tag_bs4(ticker, meta, limit=4)
        all_news.extend(rss_rows)
        all_news.extend(cnbc_rows)
        market_snapshots.append(fetch_yahoo_market_snapshot(ticker, meta["yahoo_symbol"]))

    if not all_news:
        print("[INFO] Menggunakan fallback berita deterministik.")
        all_news = fallback_records(now_iso)

    df = pd.DataFrame(all_news).drop_duplicates(subset=["news_id"]).reset_index(drop=True)
    df.insert(0, "timestamp_utc", now_iso)

    csv_path = os.path.join(out_dir, "telecom_news_scraped.csv")
    json_path = os.path.join(out_dir, "telecom_news_scraped.json")
    summary_path = os.path.join(out_dir, "scraping_summary.json")

    df.to_csv(csv_path, index=False, encoding="utf-8")
    df.to_json(json_path, orient="records", indent=2, force_ascii=False)

    summary = {
        "scraped_at_utc": now_iso,
        "total_articles": int(len(df)),
        "per_ticker": df["ticker"].value_counts().to_dict(),
        "sentiment_distribution": df["sentiment_label"].value_counts().to_dict(),
        "channels": df["ingestion_channel"].value_counts().to_dict(),
        "market_snapshots": market_snapshots,
    }
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="TCBA Telecom Web Scraping Pipeline")
    parser.add_argument("--out-dir", default="output", help="Direktori output hasil scraping")
    args = parser.parse_args()
    run_scraping(args.out_dir)


if __name__ == "__main__":
    main()
