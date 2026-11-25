# TCBA Individual Project — CI/CD Pipeline Data Sektor Telekomunikasi (Azure & GitHub Actions)

- **Mahasiswa:** Raihan Ade Alfattah
- **NIM:** L0224009
- **Kelas:** A
- **Mata Kuliah:** Cloud Technology for Big Data and Data Analytics (TCBA) — Universitas Sebelas Maret

## Tema Final Project (Kelompok 7)
*Prediksi Arah Fluktuasi Angka Rasio Profitabilitas Perusahaan Sektor Jaringan Telekomunikasi Indonesia (`TLKM`, `ISAT`, `EXCL`) Berbasis Cloud Azure melalui Integrasi Data Pasar Keuangan, Makroekonomi, dan Sentimen Berita Industri.*

## Struktur Repositori
```text
tcba-cicd-telecom-scraping/
├── .github/workflows/
│   └── ci-cd-pipeline.yml        # Workflow CI/CD + scheduler cron 6 jam + OIDC deploy
├── src/
│   ├── config.py                 # Konfigurasi emiten TLKM/ISAT/EXCL & threshold sentimen
│   ├── ingest.py                 # Google News RSS, CNBC & Kontan BS4, Yahoo Finance, Frankfurter FX
│   ├── transform.py              # Pembersihan judul, skor sentimen leksikon, skema standar
│   ├── validate.py               # Validasi data-contract & konsistensi artefak CSV/JSON
│   ├── pipeline.py               # Orkestrator CLI mode fixture (CI) dan live (CD/scheduler)
│   └── upload_blob.py            # Upload terautentikasi OIDC ke Azure Blob Storage
├── tests/
│   ├── unit/                     # Unit test config, transform, dan validate
│   └── integration/              # Integration test end-to-end mode fixture
├── data/sample/sample_payload.json
├── .env.example
├── requirements.txt
└── requirements-dev.txt
```

## Cara Menjalankan Lokal
```bash
pip install -r requirements-dev.txt
pytest -v
python -m src.pipeline fixture --out-dir data/fixture_out
python -m src.pipeline live --out-dir data/live_out
```

## Arsitektur CI/CD & Scheduler 6 Jam
1. **Continuous Integration (`test`):** Berjalan otomatis pada `push` (`main`, `feature/**`) dan `pull_request` ke `main` untuk menjalankan `pytest -v`, validasi pipeline fixture, dan menyimpan artefak `telecom-pipeline-fixture-output`.
2. **Continuous Deployment (`deploy`):** Berjalan pada `main` saat jadwal `schedule` (`cron: "0 */6 * * *"`, setiap 6 jam) atau pemicu manual `workflow_dispatch` (`deploy_to_azure: true`).
3. **Autentikasi Passwordless & Storage Azure:** Menggunakan Microsoft Entra ID App Registration + OIDC Federated Credentials (`azure/login@v2`) tanpa menyimpan client secret di repositori, lalu menyimpan data `raw/`, `processed/`, dan `metadata/` ke container privat `telecom-cicd-data` pada Storage Account `sttcba09cicd`.
