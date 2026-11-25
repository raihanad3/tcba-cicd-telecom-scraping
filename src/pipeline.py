"""Orkestrator pipeline ingestion data telekomunikasi (mode fixture untuk CI, mode live untuk CD/scheduler)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.ingest import ingest_live_payload, load_fixture_payload
from src.transform import transform_payload
from src.validate import validate_dataframe, validate_output_files

DEFAULT_FIXTURE_PATH = Path("data/sample/sample_payload.json")


def run_pipeline(
    mode: str,
    out_dir: str | Path,
    fixture_path: str | Path = DEFAULT_FIXTURE_PATH,
) -> dict[str, Any]:
    """Menjalankan ingestion -> transformasi -> validasi -> penyimpanan artefak raw/processed/metadata."""
    if mode == "fixture":
        raw_payload = load_fixture_payload(fixture_path)
    elif mode == "live":
        raw_payload = ingest_live_payload()
    else:
        raise ValueError(f"Mode pipeline tidak dikenali: {mode}")

    df, summary = transform_payload(raw_payload)
    validate_dataframe(df)

    root = Path(out_dir)
    raw_dir = root / "raw"
    processed_dir = root / "processed"
    metadata_dir = root / "metadata"
    for directory in (raw_dir, processed_dir, metadata_dir):
        directory.mkdir(parents=True, exist_ok=True)

    for ticker in ("TLKM", "ISAT", "EXCL"):
        emiten_block = raw_payload["emitens"][ticker]
        raw_file = raw_dir / f"{ticker.lower()}_raw.json"
        raw_file.write_text(json.dumps(emiten_block, indent=2, ensure_ascii=False), encoding="utf-8")

    (raw_dir / "macro_fx_raw.json").write_text(
        json.dumps(raw_payload["macro_fx"], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    csv_path = processed_dir / "telecom_ingestion.csv"
    json_path = processed_dir / "telecom_ingestion.json"
    meta_path = metadata_dir / "run_metadata.json"

    df.to_csv(csv_path, index=False, encoding="utf-8")
    df.to_json(json_path, orient="records", indent=2, force_ascii=False)
    meta_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    validate_output_files(root)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="TCBA Telecom Profitability Data Ingestion Pipeline")
    parser.add_argument("mode", choices=["fixture", "live"], help="Mode eksekusi: fixture (CI) atau live (CD/cron)")
    parser.add_argument("--out-dir", default="data/live_out", help="Direktori target penyimpanan raw/processed/metadata")
    parser.add_argument("--fixture-path", default=str(DEFAULT_FIXTURE_PATH), help="Path file JSON fixture")
    args = parser.parse_args()

    summary = run_pipeline(mode=args.mode, out_dir=args.out_dir, fixture_path=args.fixture_path)
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
