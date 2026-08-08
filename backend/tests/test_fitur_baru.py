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
    t = client.post("/api/auth/login", json={"username": "dokter", "password": "dokter123"}).json()["access_token"]
    # nonaktifkan dokter oleh admin
    dokter_id = client.get("/api/users", headers=ha, params={"q": "dokter"}).json()[0]["id"]
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
    r = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert r.status_code == 200
    return r.json()["access_token"]


# ===== Fitur 2: profil & ganti password sendiri =====
def test_profil_dan_ganti_password(client, dokter_token):
    h = auth(dokter_token)

    # ganti nama sendiri
    r = client.put("/api/auth/me", headers=h, json={"nama": "Dr. Andini Wijaya"})
    assert r.status_code == 200
    assert r.json()["nama"] == "Dr. Andini Wijaya"

    # ganti password: password lama salah -> 400
    assert client.post("/api/auth/me/password", headers=h,
                       json={"old_password": "salah", "new_password": "baru123"}).status_code == 400

    # ganti password benar -> bisa login dengan password baru
    assert client.post("/api/auth/me/password", headers=h,
                       json={"old_password": "dokter123", "new_password": "dokterBaru1"}).status_code == 200
    r = client.post("/api/auth/login", json={"username": "dokter", "password": "dokterBaru1"})
    assert r.status_code == 200

    # kembalikan password biar test lain tidak terganggu
    h2 = auth(r.json()["access_token"])
    client.post("/api/auth/me/password", headers=h2,
                json={"old_password": "dokterBaru1", "new_password": "dokter123"})


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
