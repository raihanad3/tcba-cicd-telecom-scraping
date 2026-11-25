"""Integration test untuk eksekusi end-to-end pipeline mode fixture dan verifikasi artefak."""

import json
from pathlib import Path

import pandas as pd

from src.pipeline import run_pipeline


def test_pipeline_fixture_end_to_end(tmp_path: Path) -> None:
    out_dir = tmp_path / "fixture_out"
    summary = run_pipeline(mode="fixture", out_dir=out_dir)

    assert summary["mode"] == "fixture"
    assert summary["total_articles"] == 4
    assert summary["per_ticker"] == {"TLKM": 2, "ISAT": 1, "EXCL": 1}

    csv_file = out_dir / "processed" / "telecom_ingestion.csv"
    meta_file = out_dir / "metadata" / "run_metadata.json"
    assert csv_file.is_file()
    assert meta_file.is_file()

    df = pd.read_csv(csv_file)
    assert len(df) == 4
    meta = json.loads(meta_file.read_text(encoding="utf-8"))
    assert meta["usd_idr_rate"] == 15890.5
