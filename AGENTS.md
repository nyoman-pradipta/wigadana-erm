# ERM Klinik — panduan agen coding

Project: Sistem Rekam Medis Elektronik klinik. Backend FastAPI + frontend Vue 3,
deploy: frontend di Vercel, backend+PostgreSQL+Redis di VPS.

## WAJIB: basecode-pipeline — jalankan SELALU, di setiap sesi/task

Ikuti skill `basecode-pipeline` — terinstall GLOBAL di `~/.claude/skills/basecode-pipeline/`
(Claude Code) dan `~/.gemini/skills/basecode-pipeline/` (agy). Kalau skill tidak ada di
mesin ini, instruksi enam layer di bawah ini tetap berlaku langsung. Enam layer, jangan
dilewati yang ada tool-nya:

1. **Graph layer (graphify)** — sebelum menjawab pertanyaan "di mana / bagaimana /
   apa yang rusak" atau sebelum mengubah kode non-trivial, gunakan graph di
   `graphify-out/`:
   - `graphify query "<pertanyaan>" --budget 2000`
   - `graphify path "A" "B"` — hubungan antar simbol
   - `graphify explain "Symbol"` — penjelasan satu simbol + tetangganya
   - `graphify affected "X"` — blast radius perubahan
   - Setelah batch edit: `graphify update .` (AST-only, tanpa API cost).
   - Edge `INFERRED` = petunjuk, bukan fakta — verifikasi dengan baca source.
2. **Design layer (Ponytail)** — ladder minimal: reuse existing → stdlib → fitur
   platform → dependency terpasang → one-liner → baru kode minimal. Tidak ada
   abstraksi yang tidak diminta, tidak ada scaffolding "untuk nanti". Fix bug =
   root cause di fungsi bersama, bukan guard per call site.
3. **Shell layer (rtk)** — perintah shell lewat `rtk` (hook aktif otomatis di
   Claude Code; di agy prefix manual `rtk git status` dsb untuk perintah baca).
4. **Output layer** — balasan ke user terse (gaya caveman), kecuali kode/commit
   (tetap normal) dan peringatan keamanan.
5. **Final reasoning** — sintesis hasil graph + verifikasi source sebelum jawab.
6. **Review layer (ecc:)** — kalau ada `ecc:code-reviewer` / `ecc:security-reviewer`
   (plugin everything-claude-code), pakai untuk perubahan non-trivial, terutama
   yang menyentuh auth/input/secrets. Kalau tidak ada: self-review vs layer 2 & 5.

## Konteks project

- `backend/app/` — FastAPI: `main.py` (app + lifespan seed user), `models.py`
  (User/Patient/Visit, SQLAlchemy 2.0 Mapped), `schemas.py` (Pydantic),
  `security.py` (PBKDF2 + JWT), `deps.py` (`get_current_user`, `require_roles`),
  `redis_client.py` (cache + counter antrian, graceful fallback kalau Redis mati),
  `pdf.py` (ReportLab, A5), `routers/` (auth, patients, antrian, visits, users, stats).
- `frontend/src/` — Vue 3 + Pinia + Vue Router + Axios: `api/client.js`
  (interceptor JWT + `openPdf` blob), `stores/auth.js`, `views/` (Login,
  DashboardView=antrian live, PasienView, PasienFormView, RiwayatView,
  PemeriksaanView, UserManagementView, StatistikView, ProfilView).
- Role: `admin` (semua), `dokter` (daftar pasien, panggil antrian, isi pemeriksaan, lihat riwayat). Role `suster` dihapus.
- Flow: pasien daftar → nomor antrian (counter Redis per hari, fallback DB) →
  dokter panggil (`menunggu`→`dipanggil`) → isi → `diperiksa` (draft) /
  `selesai` (diagnosa+terapi terisi) → masuk riwayat pasien (cache Redis 60s).

## Perintah

- Backend test: `cd backend && .venv/bin/python -m pytest` (10 test, sqlite temp,
  tanpa infra — wajib pass sebelum selesai).
- Frontend build: `cd frontend && NODE_ENV=development npm run build`
  (CATATAN: shell user punya `NODE_ENV=production` global, devDeps perlu override).
- Run backend dev: `cd backend && DATABASE_URL=sqlite:///./erm_dev.db .venv/bin/uvicorn app.main:app --reload`
- Run frontend dev: `cd frontend && NODE_ENV=development npx vite`
- User default: admin/123456, wigadana/123456.
- API docs: http://localhost:8000/docs saat backend jalan.

## Konvensi

- Bahasa kode/komentar: Inggris; pesan error API & UI: Bahasa Indonesia.
- JWT via header Bearer; jangan pernah buat jalur auth lewat query param.
- Password: `hash_password`/`verify_password` (PBKDF2) — jangan plaintext.
- Cache Redis: `cache_get/cache_set` + invalidate prefix di write; kalau Redis
  mati aplikasi TETAP jalan (fallback DB) — jangan patahkan ini.
- Data medis = sensitif: jangan log isi rekam medis, batasi akses per role.
