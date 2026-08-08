Baca kode kelar. Konvensi kepegang: FastAPI router per resource, `require_roles()` dep, PBKDF2+JWT di security.py, Redis cache-aside dgn graceful degrade, SQLAlchemy 2.0 Mapped style, no Alembic (cuma `Base.metadata.create_all`), Vue3 composition API + Pinia store token/user di localStorage, sidebar di `AppLayout.vue`.

Berikut design spec-nya:

```markdown
# Design Spec — 4 Fitur Baru ERM Klinik

Konvensi mengikuti kode existing: FastAPI router per resource (prefix `/api/...`),
`require_roles("admin", ...)` dari `deps.py`, PBKDF2+JWT di `security.py`,
Redis cache-aside (`cache_get/cache_set/cache_delete_prefix`, graceful degrade
kalau Redis mati), SQLAlchemy 2.0 `Mapped` style, **tidak ada Alembic** — schema
baru butuh migrasi manual (`ALTER TABLE`) untuk DB yang sudah jalan, karena
`Base.metadata.create_all()` di `main.py` cuma bikin tabel baru, tidak
menambah kolom ke tabel lama.

---

## 1. Kelola Akun Dokter/Staf (role admin)

### Model DB
`User` (`backend/app/models.py`) tambah kolom, tanpa hard delete karena FK
`visits.doctor_id`:

```python
is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
```

Migrasi manual buat DB existing: `ALTER TABLE users ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT true;`

`auth.login` dan `deps.get_current_user` wajib cek `user.is_active` — kalau
false: login ditolak 401 "Akun dinonaktifkan", dan token lama yang masih
berlaku juga langsung ditolak di `get_current_user` (bukan cuma di login).

### Endpoint (`routers/users.py`, baru)
- `GET /api/users?q=&role=&is_active=` — list, role admin only. Response `list[UserOut]` (tambah `is_active` di `UserOut`).
- `POST /api/users` — body `{username, password, nama, role}` → create. Cek username unik (409 kalau dupe). Hash password via `hash_password`.
- `PUT /api/users/{id}` — body `UserAdminUpdate{nama?, role?, is_active?}` (partial, `exclude_unset`). Ini juga jalur nonaktifkan/aktifkan user (set `is_active`), **bukan** `DELETE` — tidak ada endpoint delete sama sekali.
- `POST /api/users/{id}/reset-password` — body `{new_password}` → admin reset password user lain tanpa tahu password lama.

Semua route pakai `Depends(require_roles("admin"))`.

### Frontend
- View baru `UserManagementView.vue`, route `/pengguna` (list + toggle aktif/nonaktif + tombol reset password → modal input password baru).
- View/modal `UserFormView.vue` atau modal inline untuk create, route `/pengguna/baru`.
- Sidebar (`AppLayout.vue`): tambah `<router-link to="/pengguna" v-if="auth.role === 'admin'">👤 Pengguna</router-link>`.
- Router guard tambahan: kalau non-admin akses `/pengguna` langsung → redirect (cukup sembunyikan link + backend 403 sudah cukup, tapi tambahkan `meta: { roles: ['admin'] }` dan cek di `router.beforeEach` biar UX rapi, bukan cuma nunggu API 403).

### Urutan implementasi
1. Model: tambah `is_active` + migrasi manual + seed default users tetap `is_active=True`.
2. Schema: `UserOut` tambah field, `UserCreate`, `UserAdminUpdate`, `PasswordResetRequest`.
3. `deps.get_current_user` & `auth.login`: guard `is_active`.
4. Router `users.py` + daftarkan di `main.py`.
5. Frontend view + sidebar link + router meta.

---

## 2. Ganti Password Sendiri + Edit Profil

Tidak perlu role khusus — pakai identitas dari token (`get_current_user`),
**bukan** path param, supaya user A tidak bisa edit user B (IDOR).

### Endpoint (`routers/auth.py`, tambah)
- `PUT /api/auth/me` — body `ProfileUpdate{nama: str}` → update nama sendiri. Response `UserOut`.
- `POST /api/auth/me/password` — body `PasswordChange{old_password, new_password}` → verify `old_password` dgn `verify_password`, kalau salah 400 "Password lama salah", kalau cocok hash `new_password` (`hash_password`) dan simpan.

### Model DB
Tidak ada perubahan.

### Frontend
- View baru `ProfilView.vue`, route `/profil` — form nama + form ganti password (2 form terpisah, 2 request).
- Setelah update nama sukses: update `auth.user` di Pinia store + `localStorage.erm_user` (biar nama di sidebar ikut berubah tanpa reload).
- Link ke `/profil` ditaruh di `user-box` sidebar (`AppLayout.vue`), dekat nama/role yang sudah ada, sebelum tombol Keluar.

### Urutan implementasi
1. Schema `ProfileUpdate`, `PasswordChange`.
2. 2 endpoint di `auth.py`.
3. View `ProfilView.vue` + route + link sidebar + sync store.

---

## 3. Export/Cetak PDF Rekam Medis & Resep

### Pilihan library: **ReportLab**
- vs WeasyPrint: WeasyPrint (HTML/CSS→PDF) lebih gampang buat layout tapi butuh dependency sistem (Cairo/Pango/GObject) — ribet di deploy (terutama Windows/serverless).
- vs fpdf2: fpdf2 pure-Python & ringan, tapi flowable/table layout-nya lebih manual, kurang cocok buat tabel resep yang butuh word-wrap otomatis.
- **ReportLab** (Platypus: `SimpleDocTemplate`, `Table`, `Paragraph`): pure-Python wheel (no system lib), font TTF bisa di-embed via `pdfmetrics.registerFont` (pakai font unicode misal DejaVuSans/NotoSans buat karakter é, ñhistoris alergi dll), support gambar (`Image` flowable, buat logo klinik), dan kontrol layout presisi buat ukuran cetak A5. Dependency baru: `reportlab` di `requirements.txt`.

### Gap data yang perlu diisi dulu
- Belum ada field nama klinik/alamat/no telp/logo — tambah `Settings` (`config.py`): `CLINIC_NAME`, `CLINIC_ADDRESS`, `CLINIC_PHONE` (env var, bukan DB — konsisten dgn pola `config.py` yang sudah ada, static per instalasi).
- Resep butuh identitas dokter (nama + no. SIP) — `User` model belum punya `no_sip`. Tambah kolom opsional: `no_sip: Mapped[str | None] = mapped_column(String(50), nullable=True)`, diisi lewat form edit user admin (fitur 1) atau profil sendiri (fitur 2).

### Endpoint (`routers/visits.py`, tambah)
- `GET /api/visits/{visit_id}/pdf/rekam-medis` — role: admin, dokter, suster (semua yang bisa lihat riwayat). Response `application/pdf` (`Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": "inline; filename=RM-{no_rm}-{visit_id}.pdf"})`).
- `GET /api/visits/{visit_id}/pdf/resep` — sama role. 404 kalau `visit.terapi` kosong (belum ada resep buat dicetak).

Generator PDF taruh di modul baru `backend/app/pdf.py` (fungsi murni `build_rekam_medis_pdf(visit) -> bytes`, `build_resep_pdf(visit) -> bytes`), dipanggil dari router — tidak nyampur logic PDF ke router.

### Layout A5 (148 x 210 mm, potrait)
**Rekam medis:**
1. Header: nama klinik (bold, besar) + alamat + telp, garis pemisah.
2. Blok identitas pasien: nama, no. RM, no. identitas, alamat — 2 kolom.
3. Blok pemeriksaan: tgl_pemeriksaan, anamnesa, TB/BB/TD/suhu/HR/RR (grid ringkas), pemeriksaan_fisik, diagnosa, terapi — tiap field pakai `Paragraph` (auto word-wrap, bukan `drawString` manual biar teks panjang gak overflow).
4. Footer: nama dokter + tanggal cetak.

**Resep:**
1. Header sama (nama klinik).
2. Blok dokter: nama + no. SIP (kanan atas, gaya resep konvensional).
3. Blok pasien: nama, umur (kalau ada), tgl.
4. Simbol "R/" + isi `terapi` sebagai daftar obat (`Table`, tiap baris = 1 item, split by newline dari field `terapi`).
5. Area tanda tangan dokter (blank space + garis, bukan gambar).

### Frontend
- Di `RiwayatView.vue` (detail kunjungan) dan `PemeriksaanView.vue`: tombol "🖨️ Cetak Rekam Medis" dan "🖨️ Cetak Resep" — `<a :href="pdfUrl" target="_blank">` bukan `axios.get` blob, biar browser langsung buka print preview. URL butuh token — karena route pakai `<a href>` (bukan axios interceptor), backend endpoint terima token via query param fallback (`?token=...`) selain header Bearer, ATAU frontend fetch via axios `responseType: 'blob'` lalu `window.open(URL.createObjectURL(blob))`. **Pilih opsi kedua** (axios blob) — konsisten dgn pola auth existing (semua request lewat interceptor), tidak perlu bikin jalur auth baru via query param yang lebih rawan bocor di log server/browser history.

### Urutan implementasi
1. `config.py`: tambah `CLINIC_NAME/ADDRESS/PHONE`. Model: tambah `User.no_sip` (nullable, migrasi manual).
2. `requirements.txt`: tambah `reportlab`, download font TTF unicode ke `backend/app/fonts/`.
3. `pdf.py`: 2 fungsi builder.
4. 2 endpoint di `visits.py`.
5. Frontend: tombol cetak + axios blob + `window.open`.

---

## 4. Statistik Dashboard

### Endpoint (`routers/stats.py`, baru)
- `GET /api/stats/overview` — role: **admin only** (data lintas dokter/staf, sensitif buat performance review). Response:
```json
{
  "total_kunjungan": 1523,
  "kunjungan_7_hari": [{"tanggal": "2026-07-29", "jumlah": 42}, ...],
  "diagnosa_terbanyak": [{"diagnosa": "ISPA", "jumlah": 88}, ...],
  "dokter_teraktif": [{"nama": "Dr. Andini", "jumlah": 210}, ...]
}
```

### Query agregasi (SQLAlchemy)
```python
# total kunjungan
db.query(func.count(Visit.id)).scalar()

# kunjungan per hari, 7 hari terakhir
sejak = date.today() - timedelta(days=6)
rows = (
    db.query(func.date(Visit.created_at).label("tgl"), func.count(Visit.id))
    .filter(Visit.created_at >= sejak)
    .group_by("tgl").order_by("tgl").all()
)
# isi tanggal yang tidak ada baris dgn 0 di Python (jangan generate_series, biar portable)

# diagnosa terbanyak (top 10) — diagnosa itu free-text, bukan kode standar (ICD),
# jadi grouping exact-match string apa adanya; catat keterbatasan ini di UI ("berdasar teks diagnosa")
(
    db.query(Visit.diagnosa, func.count(Visit.id))
    .filter(Visit.diagnosa.isnot(None), Visit.diagnosa != "")
    .group_by(Visit.diagnosa)
    .order_by(func.count(Visit.id).desc())
    .limit(10).all()
)

# dokter teraktif (top 5)
(
    db.query(User.nama, func.count(Visit.id))
    .join(Visit, Visit.doctor_id == User.id)
    .group_by(User.id, User.nama)
    .order_by(func.count(Visit.id).desc())
    .limit(5).all()
)
```

### Cache Redis?
**Ya** — pola sama dgn `cache_get/cache_set` existing. Key `stats:overview`,
TTL 300 detik (5 menit) — statistik agregat gak perlu realtime kayak antrian
(TTL 30d), dan query-nya 4x full-table scan/group-by yang lebih berat dari
query antrian biasa. Invalidasi: **tidak perlu manual delete** (beda dari
`riwayat`/`antrian` yang di-invalidate tiap ada perubahan) — cukup andalkan
TTL expire, karena data statistik toleran delay 5 menit.

### Frontend
- View baru `StatistikView.vue`, route `/statistik` — 4 card (total, chart 7 hari pakai bar sederhana/table, tabel diagnosa terbanyak, tabel dokter teraktif). Tidak perlu chart library baru — SVG/CSS bar manual cukup buat 7 titik data (ladder: skip dependency baru buat use-case sesederhana ini).
- Sidebar: `<router-link to="/statistik" v-if="auth.role === 'admin'">📊 Statistik</router-link>`.
- Router meta `{ roles: ['admin'] }` + guard di `router/index.js`.

### Urutan implementasi
1. Endpoint `stats.py` + 3 query + cache.
2. Daftarkan router di `main.py`.
3. Frontend view + sidebar + route guard.

---

## Ringkasan Urutan Lintas-Fitur (kalau dikerjakan berurutan)
1. Fitur 2 (ganti password/profil) — paling kecil, tidak nyentuh model.
2. Fitur 1 (kelola user) — butuh migrasi `is_active`, dependency buat fitur lain (reset password admin overlap dgn fitur 2).
3. Fitur 4 (statistik) — independen, tidak nyentuh model.
4. Fitur 3 (PDF) — paling besar (dependency baru + font + gap data `no_sip`/nama klinik), kerjakan terakhir.
```

Siap. Spec cakup endpoint, model, frontend, role, urutan tiap fitur — tanpa nulis/ubah file (sesi desain aja).
