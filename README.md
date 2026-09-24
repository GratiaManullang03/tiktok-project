# TikTok Product Research

[![CI](https://github.com/GratiaManullang03/tiktok-project/actions/workflows/ci.yml/badge.svg)](https://github.com/GratiaManullang03/tiktok-project/actions/workflows/ci.yml)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Neon-336791?logo=postgresql)](https://neon.tech/)
[![Groq](https://img.shields.io/badge/LLM-Groq-F55036)](https://groq.com/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)](https://docs.docker.com/compose/)

Personal tool untuk riset produk TikTok Shop, dengan pipeline:

```
Product Data → Scraper/API → Product Scoring → LLM Analysis
```

Backend **FastAPI** + **PostgreSQL** (Neon), akses data pakai **raw SQL (psycopg2)** - bukan ORM, Clean Architecture (api → services → repositories → schemas), tanpa auth (single-user, personal tool, repo private).

Data produk diambil dari **search API publik Tokopedia** (gratis, tidak butuh API key) - bukan dari domain `shop.tiktok.com` langsung, karena itu captcha-walled untuk visitor anonim. Ini tetap representatif untuk riset TikTok Shop Indonesia karena katalognya sudah merger ke Tokopedia sejak 2023 (tiap produk masih bawa `ttsProductID`/seller id TikTok Shop di response-nya).

---

## 📑 Table of Contents

- [Quick Start](#-quick-start)
- [Alur Kerja](#-alur-kerja)
- [API Design](#-api-design)
- [Database](#-database)
- [Konfigurasi](#-konfigurasi-penting-env)
- [Project Structure](#-project-structure)
- [Testing & CI](#-testing--ci)
- [Notes](#-notes)

---

## 🚀 Quick Start

DB pakai Postgres eksternal (Neon) - isi `PGHOST`/`PGDATABASE`/`PGUSER`/`PGPASSWORD`/`PGSSLMODE`/`PGCHANNELBINDING` di `.env`, tidak ada container Postgres lokal.

### Dengan Docker

```bash
git clone git@github.com:GratiaManullang03/tiktok-project.git
cd tiktok-project
cp .env.example .env
# isi PGHOST/PGDATABASE/PGUSER/PGPASSWORD, GROQ_API_KEY di .env
docker-compose up --build
docker-compose exec app alembic upgrade head   # jalankan sekali di awal / tiap ada migration baru
```

API tersedia di [http://localhost:8000](http://localhost:8000), docs di [http://localhost:8000/docs](http://localhost:8000/docs)

### Manual (development)

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# isi kredensial Postgres eksternal di .env
alembic upgrade head          # buat schema "tiktok" + semua tabel
uvicorn app.main:app --reload --port 8000
```

---

## 🔄 Alur Kerja

1. **`POST /api/v1/scrape/run`** dengan `{"keyword": "..."}` — menjalankan scraper (search API publik Tokopedia, gratis, tidak butuh API key) di background, menyimpan produk + metric snapshot, lalu otomatis menghitung skor tiap produk.
   Skor velocity butuh minimal 2 snapshot dan growth butuh 3 (angka terjual dari Tokopedia itu total seumur produk, jadi yang dihitung selisih antar-scrape). Jadwalkan scrape ulang harian:
   ```bash
   python scripts/rescrape.py            # scrape ulang semua keyword yang pernah dipakai
   # cron: 0 7 * * * cd /path/to/tiktok-project && venv/bin/python scripts/rescrape.py
   ```
2. **`GET /api/v1/products`** — daftar produk terurut berdasarkan skor tertinggi.
3. **`POST /api/v1/products/{id}/analyze`** — memicu analisis LLM (Groq) untuk satu produk: ringkasan, kekuatan, risiko, target audiens, sudut pandang marketing, dan verdict (buy/watch/avoid).

Docs interaktif lengkap semua endpoint ada di `/docs` (Swagger) setelah server jalan.

---

## 🧭 API Design

**Pagination** - hanya di collection resource (`GET /products`, `GET /scrape/jobs`), bentuknya:

```json
{
  "success": true,
  "message": "...",
  "data": [...],
  "pagination": {
    "page": 1,
    "per_page": 10,
    "total": 125,
    "total_pages": 13,
    "has_next": true,
    "has_previous": false
  }
}
```

Single resource (`GET /products/{id}`, `GET /scrape/jobs/{id}`) tidak dipaginasi, langsung `{success, message, data}`.

**Endpoint produk:**

| Method | Path | Guna |
|---|---|---|
| GET | `/products` | List (paginated) |
| GET | `/products/{id}` | Detail (single resource, tidak dipaginasi) |
| PUT | `/products/{id}` | **Full replace** - semua field editable wajib dikirim |
| PATCH | `/products/{id}` | **Partial update** - hanya field yang dikirim yang berubah |
| DELETE | `/products/{id}` | **Soft delete** (lihat bagian Database) |
| POST | `/products/{id}/analyze` | Trigger LLM analysis |

Field yang immutable (tidak bisa diubah lewat PUT/PATCH): `mp_id`, `mp_external_id`, `mp_source`, `mp_last_scraped_at`, `created_at` - identitas & provenance dari scraper, bukan sesuatu yang masuk akal diedit manual.

---

## 🗄 Database

Struktur tabel & penamaan mengikuti konvensi di [`docs/ERDRULES.md`](docs/ERDRULES.md): prefix tabel (`mst_`/`his_`/`trx_`), primary key = singkatan tabel + `_id`, foreign key = `<prefix_sendiri>_<pk_tabel_acuan>`.

| Tabel | Jenis | Isi |
|---|---|---|
| `mst_product` | Master dinamis | Produk TikTok Shop yang dipantau |
| `his_product_metric` | History | Snapshot metrik (sales, rating, dst) tiap kali di-scrape |
| `his_product_score` | History | Hasil hitung skor tiap kali di-recompute |
| `his_product_analysis` | History | Hasil analisis LLM tiap kali dijalankan |
| `trx_scrape_job` | Transaksi | Satu eksekusi job scraping dengan lifecycle status |

**Deviasi sadar dari ERDRULES**: kolom `created_by`/`updated_by`/`deleted_by` **tidak dipakai** - ini personal tool tanpa sistem akun, jadi tidak ada aktor nyata untuk dicatat. Mengisi field itu dengan string palsu ("system") hanya menambah data yang terlihat informatif padahal tidak. `created_at`/`updated_at`/`is_deleted`/`deleted_at` tetap dipakai karena tidak butuh identitas user.

**Soft delete** dipakai untuk `mst_product` (bukan hard delete): `DELETE /products/{id}` cuma set `is_deleted=true, deleted_at=now()`. Alasannya, produk adalah induk dari `his_product_score` & `his_product_analysis` - hard delete akan bikin history riset jadi yatim/rusak. Produk yang di-soft-delete otomatis hilang dari `GET /products` dan `GET /products/{id}` (404).

**Migrations** pakai Alembic, gaya mirip Laravel - hand-written (bukan autogenerate, karena tidak ada ORM), setiap perubahan skema adalah satu file migration dengan `upgrade()`/`downgrade()` eksplisit.

```bash
alembic revision -m "add xyz column"   # ~ php artisan make:migration
alembic upgrade head                   # ~ php artisan migrate
alembic downgrade -1                   # ~ php artisan migrate:rollback
```

**Transaksi**: semua write multi-langkah (scrape → simpan produk → simpan metrik → hitung skor; atau hitung skor → simpan analisis LLM) dibungkus satu transaksi - `commit()` di akhir kalau semua langkah sukses, `rollback()` kalau ada yang gagal di tengah (atomicity, all-or-nothing). Repository layer (`app/repositories/`) sendiri tidak pernah auto-commit; boundary transaksi selalu dipegang oleh caller (service/endpoint).

---

## 🔧 Konfigurasi Penting (`.env`)

| Variabel | Keterangan |
|---|---|
| `PGHOST` / `PGDATABASE` / `PGUSER` / `PGPASSWORD` / `PGSSLMODE` / `PGCHANNELBINDING` | kredensial Postgres eksternal (Neon) |
| `GROQ_API_KEY` / `GROQ_MODEL` | kredensial & model Groq untuk tahap LLM Analysis (model harus dukung `json_mode`, cek `docs/models.json`) |
| `SCORE_WEIGHT_*` | bobot formula scoring (sales velocity, growth, rating, competition) - total wajib 1.0, app gagal start kalau tidak |

`.env` sudah di-`.gitignore` — jangan pernah commit file itu. Pakai `.env.example` sebagai referensi. Jalankan `python scripts/fetch_groq_models.py` sewaktu-waktu untuk refresh `docs/models.json` kalau line-up model Groq berubah.

---

## 📁 Project Structure

```
app/
├── api/          # Endpoint FastAPI (v1)
├── core/         # Config
├── db/           # Koneksi psycopg2 (get_db dependency)
├── schemas/      # Pydantic schemas (request/response)
├── repositories/ # Data access layer - raw SQL via psycopg2
└── services/     # Business logic: scrapers/, scoring, llm_analysis, pipeline
migrations/       # Alembic - migration schema, hand-written
docs/             # ERDRULES.md, models.json (snapshot katalog model Groq)
scripts/          # Utility script (fetch_groq_models.py, rescrape.py)
tests/            # Unit test (scoring formula, wiring pipeline, parser scraper)
```

---

## ✅ Testing & CI

```bash
pytest
```

GitHub Actions (`.github/workflows/ci.yml`) menjalankan test yang sama otomatis di setiap push/PR ke `main` — tidak butuh DB/API key asli karena `tests/conftest.py` sudah nyetel env dummy dan semua dependency eksternal (DB, Groq) di-mock di level test.

---

## 📝 Notes

- Repo ini **private** — tanpa lisensi (all rights reserved by default), karena melibatkan scraping (search API publik Tokopedia) yang berada di area abu-abu dari sisi ToS.
- **Raw SQL, bukan ORM** — akses data lewat psycopg2 langsung (`app/repositories/`), bukan SQLAlchemy ORM. Alembic (tool migration) tetap pakai SQLAlchemy secara internal, tapi itu murni urusan tooling migration, bukan query layer aplikasi.
- Tidak ada Redis/Celery — status job disimpan di tabel `trx_scrape_job`, job dijalankan lewat `BackgroundTasks` bawaan FastAPI. Cukup untuk beban personal tool; upgrade ke Celery+Redis kalau nanti butuh queue/retry lintas proses.
- Tidak ada auth — personal tool single-user, makanya juga tidak ada kolom `created_by`/`updated_by`/`deleted_by`.
