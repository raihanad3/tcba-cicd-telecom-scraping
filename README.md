# TCBA Individual Project — CI/CD Web Scraping Telekomunikasi (Azure & GitHub Actions)

- **Mahasiswa:** Raihan Ade Alfattah
- **NIM:** L0224009
- **Kelas:** A
- **Mata Kuliah:** Teknologi Cloud untuk Big Data & Analitik (TCBA)

## Tema Final Project
*Prediksi Arah Fluktuasi Angka Rasio Profitabilitas Perusahaan Sektor Jaringan Telekomunikasi Indonesia (`TLKM`, `ISAT`, `EXCL`) Berbasis Cloud Azure melalui Integrasi Data Pasar Keuangan, Makroekonomi, dan Sentimen Berita Industri.*

## Arsitektur CI/CD Pipeline
1. **Source Code Python (`scraper.py`, `test_scraper.py`, `upload_azure.py`):**
   - Mengambil berita industri telekomunikasi (`TLKM`, `ISAT`, `EXCL`) melalui Google News RSS & CNBC Indonesia (`BeautifulSoup4`), ringkasan harga pasar Yahoo Finance, serta klasifikasi sentimen leksikon keuangan Indonesia.
2. **Multi-Branch Strategy (`main` & `dev`):**
   - Pengembangan fitur dikerjakan di branch `dev`, diverifikasi via GitHub Actions CI pada Pull Request, lalu di-merge ke `main`.
3. **Continuous Integration (CI):**
   - Menjalankan `python scraper.py` dan memvalidasi kelengkapan skema CSV/JSON via `python test_scraper.py`.
4. **Continuous Deployment (CD):**
   - Autentikasi *passwordless* menggunakan **Microsoft Entra ID App Registration + OIDC Federated Credentials** (`azure/login@v2`).
   - Menyimpan output ke **Azure Blob Storage** (`sepatubola` pada container `telecom-scraping` dan `bronze`).
5. **Scheduler 6 Jam & Manual Dispatch:**
   - Dijalankan otomatis setiap 6 jam dengan `cron: '0 */6 * * *'` serta mendukung pemicu manual `workflow_dispatch`.
