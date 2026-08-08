# ERM Klinik — Sistem Rekam Medis Elektronik Sederhana

Alur sesuai diagram: **pasien daftar → dapat nomor antrian → dokter panggil → periksa → riwayat tersimpan.**

## Arsitektur

```
┌─────────────┐   HTTPS    ┌──────────────────────────┐
│  Frontend   │ ─────────▶ │  Backend API (FastAPI)   │
│  Vue 3      │            │  :8000                   │
│  (Vercel)   │            └───────┬───────────┬──────┘
└─────────────┘                    │           │
                        ┌──────────▼──┐  ┌─────▼─────┐
                        │ PostgreSQL  │  │  Redis    │
                        │ data pasien │  │ cache +   │
                        │ & rekam     │  │ nomor     │
                        │ medis       │  │ antrian   │
                        └─────────────┘  └───────────┘
```

- **Frontend** — Vue 3 + Vite + Pinia + Vue Router + Axios → deploy di **Vercel** (static).
- **Backend** — FastAPI + SQLAlchemy + JWT auth → deploy di **VPS** (Docker).
- **Cache** — Redis: cache daftar antrian (TTL 30s), cache riwayat pasien (TTL 60s), counter nomor antrian harian. **Kalau Redis mati, aplikasi tetap jalan** (fallback ke DB, cache off).
- **DB** — PostgreSQL. Tabel: `users`, `patients`, `visits`.

## Fitur

- 🔐 Login 2 role: `admin`, `dokter` (JWT bearer)
- 👥 Registrasi pasien: nomor RM otomatis (`RM-000001`), nama, alamat, no KTP/KITAS/PASSPORT, no HP, riwayat alergi
- 🪪 Antrian: daftar → dapat nomor (counter Redis per hari, reset otomatis), dokter panggil, display nomor sedang dipanggil, refresh live 5 detik
- ✍️ Pemeriksaan dokter: tanggal, anamnesa, tanda vital (TB BB TD Suhu HR RR), pemeriksaan fisik, diagnosa, terapi
- 📋 Riwayat pasien: semua pemeriksaan + dokter yang menangani, cache Redis
- 👤 Kelola akun (admin): buat user, toggle aktif/nonaktif (soft-delete, riwayat aman), reset password
- 🔑 Ganti password sendiri + edit profil (nama, no. SIP)
- 🖨️ Export PDF A5: rekam medis & resep (ReportLab, unicode font otomatis, header nama klinik)
- 📊 Statistik (admin): total kunjungan, grafik 7 hari, diagnosa terbanyak, dokter teraktif — cache Redis 5 menit

## Struktur

```
wigadana-erm/
├── backend/
│   ├── app/
│   │   ├── main.py            # entrypoint + seed user default
│   │   ├── config.py          # env config
│   │   ├── database.py        # SQLAlchemy engine
│   │   ├── models.py          # User, Patient, Visit
│   │   ├── schemas.py         # Pydantic
│   │   ├── security.py        # PBKDF2 + JWT
│   │   ├── redis_client.py    # cache + counter (graceful fallback)
│   │   ├── deps.py            # get_current_user, require_roles
│   │   └── routers/           # auth, patients, antrian, visits
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── api/client.js      # axios + interceptor JWT
│   │   ├── stores/auth.js     # pinia
│   │   ├── router/index.js
│   │   ├── layout/AppLayout.vue
│   │   └── views/             # Login, Dashboard(antrian), Pasien, Pemeriksaan, Riwayat
│   ├── vercel.json            # SPA rewrite
│   └── vite.config.js         # proxy /api → localhost:8000 (dev)
├── docker-compose.yml         # VPS: db + redis + backend
└── README.md
```

## Jalankan Lokal (Dev)

```bash
# 1. Backend (butuh Python 3.11+)
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt   # runtime + pytest + httpx
cp .env.example .env
# tanpa PostgreSQL? pakai sqlite untuk coba-coba:
export DATABASE_URL="sqlite:///./erm_dev.db"
export REDIS_URL="redis://localhost:6379/0"   # kalau ga ada redis, biarkan — fallback otomatis
uvicorn app.main:app --reload --port 8000
# → docs API: http://localhost:8000/docs

# 2. Test API (sqlite temp + redis fallback — jalan tanpa infra)
pytest tests/ -v

# 3. Frontend
cd frontend
npm install
npm run dev
# → http://localhost:5173 (proxy /api → :8000)
```

**User default (GANTI password setelah deploy!):**

| username | password | role |
|----------|----------|------|
| admin | 123456 | admin |
| wigadana | 123456 | dokter |

## Deploy ke VPS (Backend + DB + Redis)

```bash
# di VPS:
git clone <repo> && cd wigadana-erm
# buat .env (DB_PASSWORD, SECRET_KEY, CORS_ORIGINS) lalu:
docker compose up -d --build
# cek: curl http://VPS_IP:8000/api/health → {"status":"ok","redis":true}
```

**Opsional — pasang reverse proxy (Caddy/Nginx) + domain + HTTPS:**

```
Caddyfile:
api.klinikmu.com {
    reverse_proxy localhost:8000
}
```

Buka port 8000 di firewall (atau 443 via Caddy). Jangan lupa set `CORS_ORIGINS` ke domain Vercel frontend.

## Deploy ke Vercel (Frontend)

1. Push repo ke GitHub, import di Vercel: root directory = `frontend`, framework = Vite.
2. Set env var di Vercel: `VITE_API_URL=https://api.klinikmu.com/api`
   (tanpa ini, frontend akan memanggil `/api` di domainnya sendiri).
3. Deploy. `vercel.json` sudah mengatur SPA rewrite.

## API Ringkas

| Method | Path | Role | Fungsi |
|--------|------|------|--------|
| POST | `/api/auth/login` | publik | login → JWT |
| GET | `/api/auth/me` | semua | profil user |
| GET | `/api/patients?q=` | semua | cari pasien |
| POST | `/api/patients` | admin, dokter | daftar pasien baru |
| PUT | `/api/patients/{id}` | admin, dokter | edit pasien |
| POST | `/api/antrian` | admin, dokter | daftar antrian → dapat nomor |
| GET | `/api/antrian` | semua | daftar antrian (cache 30s) |
| GET | `/api/antrian/saat-ini` | semua | nomor sedang dipanggil |
| POST | `/api/antrian/{id}/panggil` | admin, dokter | dokter memanggil |
| GET | `/api/visits/riwayat/{patient_id}` | semua | riwayat pasien (cache 60s) |
| PUT | `/api/visits/{id}` | admin, dokter | isi pemeriksaan |
| GET | `/api/visits/{id}/pdf/rekam-medis` | semua | PDF rekam medis A5 |
| GET | `/api/visits/{id}/pdf/resep` | semua | PDF resep A5 |
| GET | `/api/users` | admin | list user |
| POST | `/api/users` | admin | buat user |
| PUT | `/api/users/{id}` | admin | edit / aktif-nonaktifkan user |
| POST | `/api/users/{id}/reset-password` | admin | reset password user |
| PUT | `/api/auth/me` | semua | edit nama/no. SIP sendiri |
| POST | `/api/auth/me/password` | semua | ganti password sendiri |
| GET | `/api/stats/overview` | admin | statistik (cache 5 menit) |

## Catatan Keamanan (wajib untuk produksi nyata)

- Ganti `SECRET_KEY` dan password default user.
- Data medis = data sensitif. Untuk produksi serius tambahkan: HTTPS wajib, rate limiting login, enkripsi at-rest disk VPS, backup PostgreSQL harian (`pg_dump` + cron), audit log akses rekam medis.
- `riwayat_alergi` dan identitas pasien tampil di frontend untuk semua user login — batasi akses per role sesuai kebijakan klinik.

## Migrasi DB (untuk DB yang sudah pernah jalan)

`create_all` hanya membuat tabel baru, tidak menambah kolom. Kalau sudah ada data, jalankan manual:

```sql
ALTER TABLE users ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT true;
ALTER TABLE users ADD COLUMN no_sip VARCHAR(50);
```

## Known limitations (hasil audit & review independen)

- **Race daftar antrian dobel** (klik ganda simultan) — cek "pasien punya antrian aktif" bukan atomic. Di produksi PostgreSQL tambahkan partial unique index:
  ```sql
  CREATE UNIQUE INDEX uq_visits_active ON visits (patient_id)
  WHERE status IN ('menunggu', 'dipanggil', 'diperiksa');
  ```
  (SQLite tidak mendukung partial index — dev aman, prod wajib tambah ini.)
- **Token JWT di localStorage** — rawan XSS (trade-off umum SPA). Mitigasi: CSP ketat di reverse proxy; idealnya httpOnly cookie (restructure auth besar, jadwalkan kalau data produksi sudah nyata).
- **Rate limit login** aktif hanya kalau Redis hidup (fallback tanpa limit kalau Redis mati — prioritas ketersediaan).
- **Diagnosa statistik** free-text, bukan ICD-10 — grouping exact-match.
- **AUDIT 2026-08-04 (Claude Code)**: 10 temuan, 2 Kritis + 1 Tinggi sudah difix (SECRET_KEY fail-fast ≥32 char, rate limit login 5×/15mnt/IP+user, auth guard endpoint pasien yang tadinya terbuka, seed password random, security headers, sub parsing aman). Sisa: CORS per-env (jangan campur localhost di produksi), pin dependency + lockfile, token expiry 12 jam tanpa revoke.
