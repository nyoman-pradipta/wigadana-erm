"""Test fitur: kelola akun (admin), profil/password sendiri, statistik, PDF."""
from conftest import auth


# ===== Fitur 1: kelola akun (admin) =====
def test_admin_kelola_user(client, dokter_token):
    h = auth(dokter_token)
    ha = auth(login_admin(client))

    # dokter (non-admin) tidak boleh akses /users -> 403
    assert client.get("/api/users", headers=h).status_code == 403

    # admin buat user baru
    r = client.post("/api/users", headers=ha, json={
        "username": "dr.budi", "password": "rahasia123",
        "nama": "Dr. Budi", "role": "dokter",
    })
    assert r.status_code == 201
    new_id = r.json()["id"]
    assert r.json()["is_active"] is True

    # username duplikat -> 409
    assert client.post("/api/users", headers=ha, json={
        "username": "dr.budi", "password": "x123456", "nama": "X", "role": "dokter",
    }).status_code == 409

    # update: no_sip + nonaktifkan
    r = client.put(f"/api/users/{new_id}", headers=ha, json={"no_sip": "SIP-2024-001", "is_active": False})
    assert r.status_code == 200
    assert r.json()["no_sip"] == "SIP-2024-001"
    assert r.json()["is_active"] is False

    # user nonaktif tidak bisa login
    assert client.post("/api/auth/login", json={"username": "dr.budi", "password": "rahasia123"}).status_code == 401

    # token lama user yang dinonaktifkan -> 401 juga
    t = client.post("/api/auth/login", json={"username": "wigadana", "password": "123456"}).json()["access_token"]
    # nonaktifkan dokter oleh admin
    dokter_id = client.get("/api/users", headers=ha, params={"q": "wigadana"}).json()[0]["id"]
    client.put(f"/api/users/{dokter_id}", headers=ha, json={"is_active": False})
    assert client.get("/api/antrian", headers=auth(t)).status_code == 401
    # aktifkan lagi
    client.put(f"/api/users/{dokter_id}", headers=ha, json={"is_active": True})

    # admin tidak bisa nonaktifkan diri sendiri
    admin_id = client.get("/api/users", headers=ha, params={"q": "admin"}).json()[0]["id"]
    assert client.put(f"/api/users/{admin_id}", headers=ha, json={"is_active": False}).status_code == 400

    # reset password
    assert client.post(f"/api/users/{new_id}/reset-password", headers=ha,
                       json={"new_password": "baru123"}).status_code == 200
    assert client.post("/api/auth/login", json={"username": "dr.budi", "password": "baru123"}).status_code == 401  # masih nonaktif


def login_admin(client):
    r = client.post("/api/auth/login", json={"username": "admin", "password": "123456"})
    assert r.status_code == 200
    return r.json()["access_token"]


# ===== Fitur 2: profil & ganti password sendiri =====
def test_profil_dan_ganti_password(client, dokter_token):
    h = auth(dokter_token)

    # ganti nama sendiri (username wajib dikirim, tetap sama)
    r = client.put("/api/auth/me", headers=h, json={"username": "wigadana", "nama": "Dr. Andini Wijaya"})
    assert r.status_code == 200
    assert r.json()["nama"] == "Dr. Andini Wijaya"

    # ganti password: password lama salah -> 400
    assert client.post("/api/auth/me/password", headers=h,
                       json={"old_password": "salah", "new_password": "baru123"}).status_code == 400

    # ganti password benar -> bisa login dengan password baru
    assert client.post("/api/auth/me/password", headers=h,
                       json={"old_password": "123456", "new_password": "dokterBaru1"}).status_code == 200
    r = client.post("/api/auth/login", json={"username": "wigadana", "password": "dokterBaru1"})
    assert r.status_code == 200

    # kembalikan password biar test lain tidak terganggu
    h2 = auth(r.json()["access_token"])
    client.post("/api/auth/me/password", headers=h2,
                json={"old_password": "dokterBaru1", "new_password": "123456"})


# ===== Fitur 4: statistik =====
def test_statistik_admin_only(client, dokter_token):
    # non-admin -> 403
    assert client.get("/api/stats/overview", headers=auth(dokter_token)).status_code == 403

    ha = auth(login_admin(client))
    r = client.get("/api/stats/overview", headers=ha)
    assert r.status_code == 200
    data = r.json()
    assert "total_kunjungan" in data
    assert len(data["kunjungan_7_hari"]) == 7
    assert all(v["jumlah"] >= 0 for v in data["kunjungan_7_hari"])
    assert isinstance(data["diagnosa_terbanyak"], list)
    assert isinstance(data["dokter_teraktif"], list)


# ===== Fitur 3: PDF rekam medis & resep =====
def test_pdf_rekam_medis_dan_resep(client, dokter_token):
    h = auth(dokter_token)
    hd = auth(dokter_token)

    p = client.post("/api/patients", headers=h, json={"nama": "Budi PDF", "no_hp": "0811"}).json()
    v = client.post("/api/antrian", headers=h, json={"patient_id": p["id"]}).json()
    client.post(f"/api/antrian/{v['id']}/panggil", headers=h)
    client.put(f"/api/visits/{v['id']}", headers=hd, json={
        "anamnesa": "Batuk 5 hari", "td": "110/70", "suhu": 37.2,
        "diagnosa": "ISPA", "terapi": "Paracetamol 500mg 3x1\nAmbroxol 30mg 3x1",
    })

    # resep
    r = client.get(f"/api/visits/{v['id']}/pdf/resep", headers=hd)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:5] == b"%PDF-"
    assert "filename=" in r.headers["content-disposition"]

    # rekam medis
    r = client.get(f"/api/visits/{v['id']}/pdf/rekam-medis", headers=h)
    assert r.status_code == 200
    assert r.content[:5] == b"%PDF-"

    # resep untuk visit tanpa terapi -> 404
    p2 = client.post("/api/patients", headers=h, json={"nama": "Tanpa Resep"}).json()
    v2 = client.post("/api/antrian", headers=h, json={"patient_id": p2["id"]}).json()
    client.put(f"/api/visits/{v2['id']}", headers=hd, json={"anamnesa": "Cek", "diagnosa": "Kontrol"})
    assert client.get(f"/api/visits/{v2['id']}/pdf/resep", headers=hd).status_code == 404

    # tanpa token -> 401
    assert client.get(f"/api/visits/{v['id']}/pdf/rekam-medis").status_code == 401


# ===== Fitur revisi: delete user (admin-only, target dokter saja) =====
def test_delete_user_hanya_admin_dan_target_dokter(client, dokter_token):
    h = auth(dokter_token)
    ha = auth(login_admin(client))

    # dokter (non-admin) tidak boleh delete -> 403
    assert client.delete("/api/users/1", headers=h).status_code == 403

    # admin buat dokter baru tanpa riwayat -> boleh dihapus
    r = client.post("/api/users", headers=ha, json={
        "username": "dr.hapus", "password": "rahasia123",
        "nama": "Dr. Dihapus", "role": "dokter",
    })
    new_id = r.json()["id"]
    assert client.delete(f"/api/users/{new_id}", headers=ha).status_code == 204
    assert client.delete(f"/api/users/{new_id}", headers=ha).status_code == 404  # sudah hilang

    # admin tidak bisa hapus akun admin lain (apalagi diri sendiri)
    admin_id = client.get("/api/users", headers=ha, params={"q": "admin"}).json()[0]["id"]
    assert client.delete(f"/api/users/{admin_id}", headers=ha).status_code == 403

    # dokter yang PUNYA riwayat visit -> tidak bisa dihapus (409)
    dokter_id = client.get("/api/users", headers=ha, params={"q": "wigadana"}).json()[0]["id"]
    assert client.delete(f"/api/users/{dokter_id}", headers=ha).status_code == 409


# ===== Fitur revisi: identitas dokter di header PDF =====
def test_pdf_header_identitas_dokter(client, dokter_token):
    h = auth(dokter_token)
    p = client.post("/api/patients", headers=h, json={"nama": "Test Header PDF"}).json()
    v = client.post("/api/antrian", headers=h, json={"patient_id": p["id"]}).json()
    client.post(f"/api/antrian/{v['id']}/panggil", headers=h)
    client.put(f"/api/visits/{v['id']}", headers=h, json={"anamnesa": "Cek", "diagnosa": "Sehat"})
    r = client.get(f"/api/visits/{v['id']}/pdf/rekam-medis", headers=h)
    assert r.status_code == 200
    assert r.content[:5] == b"%PDF-"


# ===== Fitur revisi: data pendaftaran pasien (agama, kewarganegaraan, status, tgl lahir -> usia) =====
def test_pasien_field_baru_dan_usia_otomatis(client, dokter_token):
    h = auth(dokter_token)
    r = client.post("/api/patients", headers=h, json={
        "nama": "Pasien Lengkap",
        "agama": "Hindu",
        "kewarganegaraan": "WNI",
        "status_perkawinan": "Menikah",
        "pekerjaan": "Petani",
        "tgl_lahir": "2000-06-15",
    })
    assert r.status_code == 201
    data = r.json()
    assert data["agama"] == "Hindu"
    assert data["kewarganegaraan"] == "WNI"
    assert data["status_perkawinan"] == "Menikah"
    assert data["pekerjaan"] == "Petani"
    assert data["tgl_lahir"] == "2000-06-15"
    assert isinstance(data["usia"], int)
    assert data["usia"] >= 24  # 2026 - 2000, minimal (belum ultah tahun ini bisa 25)

    # tanpa tgl_lahir -> usia None (bukan error/crash)
    r2 = client.post("/api/patients", headers=h, json={"nama": "Tanpa Tgl Lahir"})
    assert r2.status_code == 201
    assert r2.json()["usia"] is None


# ===== Fitur revisi: surat keterangan sakit =====
def test_surat_sakit_pdf(client, dokter_token):
    h = auth(dokter_token)
    p = client.post("/api/patients", headers=h, json={
        "nama": "Pasien Sakit", "pekerjaan": "Karyawan", "tgl_lahir": "1995-01-01",
    }).json()
    v = client.post("/api/antrian", headers=h, json={"patient_id": p["id"]}).json()
    client.post(f"/api/antrian/{v['id']}/panggil", headers=h)

    # belum isi tanggal istirahat -> 404
    assert client.get(f"/api/visits/{v['id']}/pdf/surat-sakit", headers=h).status_code == 404

    r = client.put(f"/api/visits/{v['id']}", headers=h, json={
        "anamnesa": "Demam", "diagnosa": "Flu",
        "surat_sakit_tgl_mulai": "2026-08-10", "surat_sakit_tgl_selesai": "2026-08-12",
    })
    assert r.status_code == 200
    assert r.json()["surat_sakit_tgl_mulai"] == "2026-08-10"

    r = client.get(f"/api/visits/{v['id']}/pdf/surat-sakit", headers=h)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:5] == b"%PDF-"

    # tanpa token -> 401
    assert client.get(f"/api/visits/{v['id']}/pdf/surat-sakit").status_code == 401


# ===== Fitur revisi: admin edit user manapun (username/nama/no_sip/password/role) =====
def test_admin_edit_semua_user(client, dokter_token):
    ha = auth(login_admin(client))

    # buat dokter target
    r = client.post("/api/users", headers=ha, json={
        "username": "dr.editme", "password": "rahasia123", "nama": "Dr. Edit Me", "role": "dokter",
    })
    uid = r.json()["id"]

    # admin ganti username, nama, no_sip, role, password sekaligus
    r = client.put(f"/api/users/{uid}", headers=ha, json={
        "username": "dr.editme2", "nama": "Dr. Sudah Diedit", "no_sip": "SIP-999",
        "role": "dokter", "password": "passwordBaru1",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["username"] == "dr.editme2"
    assert data["nama"] == "Dr. Sudah Diedit"
    assert data["no_sip"] == "SIP-999"

    # login dengan username & password baru harus berhasil
    r = client.post("/api/auth/login", json={"username": "dr.editme2", "password": "passwordBaru1"})
    assert r.status_code == 200

    # username bentrok dengan user lain -> 409
    r = client.put(f"/api/users/{uid}", headers=ha, json={"username": "wigadana"})
    assert r.status_code == 409

    # non-admin tidak boleh edit user lain -> 403
    h = auth(dokter_token)
    r = client.put(f"/api/users/{uid}", headers=h, json={"nama": "Hacked"})
    assert r.status_code == 403

    # cleanup
    client.delete(f"/api/users/{uid}", headers=ha)


def test_user_edit_profil_sendiri_dengan_username(client, dokter_token):
    h = auth(dokter_token)
    r = client.put("/api/auth/me", headers=h, json={"username": "wigadana", "nama": "Dr. Wiga", "no_sip": "SIP-1"})
    assert r.status_code == 200
    assert r.json()["username"] == "wigadana"

    # username bentrok punya admin -> 409
    r = client.put("/api/auth/me", headers=h, json={"username": "admin", "nama": "Dr. Wiga"})
    assert r.status_code == 409


# ===== Fitur revisi: admin bisa hapus data pasien =====
def test_admin_hapus_pasien(client, dokter_token):
    h = auth(dokter_token)
    ha = auth(login_admin(client))

    # pasien tanpa riwayat -> admin bisa hapus
    p = client.post("/api/patients", headers=h, json={"nama": "Pasien Dihapus Admin"}).json()
    assert client.delete(f"/api/patients/{p['id']}", headers=ha).status_code == 204
    assert client.get(f"/api/patients/{p['id']}", headers=h).status_code == 404

    # dokter (non-admin) tidak boleh hapus pasien -> 403
    p2 = client.post("/api/patients", headers=h, json={"nama": "Pasien Test 403"}).json()
    assert client.delete(f"/api/patients/{p2['id']}", headers=h).status_code == 403

    # pasien dengan riwayat visit -> tidak bisa dihapus (409)
    v = client.post("/api/antrian", headers=h, json={"patient_id": p2["id"]}).json()
    client.post(f"/api/antrian/{v['id']}/panggil", headers=h)
    client.put(f"/api/visits/{v['id']}", headers=h, json={"anamnesa": "Cek", "diagnosa": "Sehat"})
    assert client.delete(f"/api/patients/{p2['id']}", headers=ha).status_code == 409


# ===== Bugfix: pasien dgn antrian batal/belum diperiksa (bukan riwayat medis nyata) HARUS bisa dihapus =====
def test_admin_hapus_pasien_dengan_antrian_batal_bukan_riwayat(client, dokter_token):
    h = auth(dokter_token)
    ha = auth(login_admin(client))

    # antrian dibatalkan (tanpa data medis apapun) -> bukan riwayat, pasien tetap bisa dihapus
    p = client.post("/api/patients", headers=h, json={"nama": "Prod Test Surat Sakit Bug"}).json()
    v = client.post("/api/antrian", headers=h, json={"patient_id": p["id"]}).json()
    r = client.post(f"/api/antrian/{v['id']}/batal", headers=h)
    assert r.status_code == 200
    assert r.json()["status"] == "batal"
    assert client.delete(f"/api/patients/{p['id']}", headers=ha).status_code == 204
    assert client.get(f"/api/patients/{p['id']}", headers=ha).status_code == 404

    # antrian masih menunggu (belum sempat diperiksa) -> juga bukan riwayat, tetap bisa dihapus
    p2 = client.post("/api/patients", headers=h, json={"nama": "Pasien Masih Menunggu"}).json()
    client.post("/api/antrian", headers=h, json={"patient_id": p2["id"]})
    assert client.delete(f"/api/patients/{p2['id']}", headers=ha).status_code == 204


# ===== Fitur revisi: edit riwayat (dokter penanggung jawab atau admin) =====
def test_edit_riwayat_dokter_penanggung_jawab_atau_admin(client, dokter_token):
    h = auth(dokter_token)
    ha = auth(login_admin(client))

    p = client.post("/api/patients", headers=h, json={"nama": "Pasien Edit Riwayat"}).json()
    v = client.post("/api/antrian", headers=h, json={"patient_id": p["id"]}).json()
    client.post(f"/api/antrian/{v['id']}/panggil", headers=h)
    r = client.put(f"/api/visits/{v['id']}", headers=h, json={"anamnesa": "Batuk", "diagnosa": "ISPA", "terapi": "Obat A"})
    assert r.status_code == 200
    assert r.json()["doctor_id"] is not None

    # dokter lain (bukan penanggung jawab) -> 403
    r = client.post("/api/users", headers=ha, json={
        "username": "dr.lain", "password": "rahasia123", "nama": "Dr. Lain", "role": "dokter",
    })
    uid_lain = r.json()["id"]
    tok_lain = client.post("/api/auth/login", json={"username": "dr.lain", "password": "rahasia123"}).json()["access_token"]
    h_lain = auth(tok_lain)
    r = client.put(f"/api/visits/{v['id']}", headers=h_lain, json={"diagnosa": "Diubah dokter lain"})
    assert r.status_code == 403

    # dokter penanggung jawab sendiri -> boleh edit
    r = client.put(f"/api/visits/{v['id']}", headers=h, json={"diagnosa": "ISPA revisi"})
    assert r.status_code == 200
    assert r.json()["diagnosa"] == "ISPA revisi"

    # admin -> boleh edit siapapun punya visit-nya
    r = client.put(f"/api/visits/{v['id']}", headers=ha, json={"diagnosa": "ISPA edit admin"})
    assert r.status_code == 200
    assert r.json()["diagnosa"] == "ISPA edit admin"

    client.delete(f"/api/users/{uid_lain}", headers=ha)


# ===== Fitur revisi: hapus riwayat (admin only) =====
def test_hapus_riwayat_admin_only(client, dokter_token):
    h = auth(dokter_token)
    ha = auth(login_admin(client))

    p = client.post("/api/patients", headers=h, json={"nama": "Pasien Hapus Riwayat"}).json()
    v = client.post("/api/antrian", headers=h, json={"patient_id": p["id"]}).json()
    client.post(f"/api/antrian/{v['id']}/panggil", headers=h)
    client.put(f"/api/visits/{v['id']}", headers=h, json={"anamnesa": "Cek", "diagnosa": "Sehat", "terapi": "-"})

    # dokter (non-admin) tidak boleh hapus -> 403
    assert client.delete(f"/api/visits/{v['id']}", headers=h).status_code == 403

    # riwayat masih muncul sebelum dihapus
    r = client.get(f"/api/visits/riwayat/{p['id']}", headers=h)
    assert len(r.json()) == 1

    # admin boleh hapus
    assert client.delete(f"/api/visits/{v['id']}", headers=ha).status_code == 204
    assert client.get(f"/api/visits/{v['id']}", headers=ha).status_code == 404
    assert client.delete(f"/api/visits/{v['id']}", headers=ha).status_code == 404  # sudah hilang

    # riwayat pasien sudah kosong (cache ter-invalidate)
    r = client.get(f"/api/visits/riwayat/{p['id']}", headers=h)
    assert len(r.json()) == 0
