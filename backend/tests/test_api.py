"""End-to-end API test: alur pasien -> antrian -> panggil -> pemeriksaan -> riwayat."""
from conftest import auth


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.json()["redis"] is False  # fallback mode di test


def test_login_gagal(client):
    r = client.post("/api/auth/login", json={"username": "dokter", "password": "salah"})
    assert r.status_code == 401


def test_tanpa_token_401(client):
    assert client.get("/api/antrian").status_code == 401


def test_alur_pasien_dan_antrian(client, dokter_token):
    h = auth(dokter_token)

    # buat 2 pasien -> nomor RM auto
    p1 = client.post(
        "/api/patients", headers=h,
        json={"nama": "Budi Santoso", "alamat": "Jl. Merdeka 1",
              "jenis_identitas": "KTP", "no_identitas": "3171010101",
              "no_hp": "081234567890", "riwayat_alergi": "penisilin"},
    )
    assert p1.status_code == 201
    p1 = p1.json()
    assert p1["no_rm"] == "RM-000001"

    p2 = client.post(
        "/api/patients", headers=h,
        json={"nama": "Siti Aminah", "jenis_identitas": "KITAS", "no_identitas": "K12345"},
    )
    assert p2.status_code == 201
    p2 = p2.json()
    assert p2["no_rm"] == "RM-000002"

    # duplikat identitas -> 409
    r = client.post(
        "/api/patients", headers=h,
        json={"nama": "Budi Lain", "no_identitas": "3171010101"},
    )
    assert r.status_code == 409

    # daftar antrian -> nomor 1 dan 2
    v1 = client.post("/api/antrian", headers=h, json={"patient_id": p1["id"]}).json()
    v2 = client.post("/api/antrian", headers=h, json={"patient_id": p2["id"]}).json()
    assert (v1["antrian_no"], v1["status"]) == (1, "menunggu")
    assert (v2["antrian_no"], v2["status"]) == (2, "menunggu")

    # daftar dobel -> 409
    assert client.post("/api/antrian", headers=h, json={"patient_id": p1["id"]}).status_code == 409

    # list antrian
    lst = client.get("/api/antrian", headers=h).json()
    assert [(x["visit"]["antrian_no"], x["patient"]["nama"]) for x in lst] == [
        (1, "Budi Santoso"), (2, "Siti Aminah")
    ]

    # panggil -> saat-ini
    assert client.post(f"/api/antrian/{v1['id']}/panggil", headers=h).json()["status"] == "dipanggil"
    kini = client.get("/api/antrian/saat-ini", headers=h).json()
    assert kini["visit"]["antrian_no"] == 1
    assert kini["patient"]["nama"] == "Budi Santoso"


def test_pemeriksaan_selesai_dan_riwayat(client, dokter_token):
    h = auth(dokter_token)
    hd = auth(dokter_token)

    p = client.post("/api/patients", headers=h, json={"nama": "Andi", "no_hp": "0811"}).json()
    v = client.post("/api/antrian", headers=h, json={"patient_id": p["id"]}).json()
    client.post(f"/api/antrian/{v['id']}/panggil", headers=h)

    # draft tanpa diagnosa -> diperiksa
    draft = client.put(
        f"/api/visits/{v['id']}", headers=hd,
        json={"anamnesa": "Pusing", "tb": 160, "bb": 55},
    ).json()
    assert draft["status"] == "diperiksa"
    assert draft["doctor"]["nama"] == "Dr. Andini"

    # lengkap -> selesai + tgl default hari ini
    done = client.put(
        f"/api/visits/{v['id']}", headers=hd,
        json={"anamnesa": "Demam 3 hari", "td": "120/80", "suhu": 38.5,
              "diagnosa": "Faringitis akut", "terapi": "Amoxicillin 500mg 3x1"},
    ).json()
    assert done["status"] == "selesai"
    assert done["doctor"]["nama"] == "Dr. Andini"

    # riwayat pasien berisi pemeriksaan + dokter penanganan
    riwayat = client.get(f"/api/visits/riwayat/{p['id']}", headers=hd).json()
    assert len(riwayat) == 1
    assert riwayat[0]["diagnosa"] == "Faringitis akut"
    assert riwayat[0]["doctor"]["nama"] == "Dr. Andini"

    # sudah selesai -> tidak tampil di antrian aktif
    lst = client.get("/api/antrian", headers=h).json()
    assert all(x["visit"]["id"] != v["id"] for x in lst)


def test_dokter_bisa_daftar_dan_panggil(client, dokter_token):
    # Role suster dihapus — dokter kini punya permission daftar pasien & panggil antrian
    r = client.post("/api/patients", headers=auth(dokter_token), json={"nama": "X"})
    assert r.status_code == 201
    pid = r.json()["id"]
    v = client.post("/api/antrian", headers=auth(dokter_token), json={"patient_id": pid}).json()
    assert client.post(f"/api/antrian/{v['id']}/panggil", headers=auth(dokter_token)).status_code == 200


def test_batal_dan_panggil_ulang_antrian(client, dokter_token):
    """Fix review agy: draft 'diperiksa' bisa dipanggil ulang; antrian bisa dibatalkan."""
    h = auth(dokter_token)
    hd = auth(dokter_token)

    p = client.post("/api/patients", headers=h, json={"nama": "Antri Batal"}).json()
    v = client.post("/api/antrian", headers=h, json={"patient_id": p["id"]}).json()
    vid = v["id"]

    # batal dari menunggu
    r = client.post(f"/api/antrian/{vid}/batal", headers=h)
    assert r.status_code == 200
    assert r.json()["status"] == "batal"
    # antrian batal tidak muncul di daftar aktif
    lst = client.get("/api/antrian", headers=h).json()
    assert all(x["visit"]["id"] != vid for x in lst)

    # panggil ulang dari 'diperiksa' (draft ditinggalkan dokter)
    p2 = client.post("/api/patients", headers=h, json={"nama": "Draft Ditinggal"}).json()
    v2 = client.post("/api/antrian", headers=h, json={"patient_id": p2["id"]}).json()
    client.post(f"/api/antrian/{v2['id']}/panggil", headers=h)
    client.put(f"/api/visits/{v2['id']}", headers=hd, json={"anamnesa": "Draft"})
    # status sekarang 'diperiksa' -> bisa dipanggil ulang
    r = client.post(f"/api/antrian/{v2['id']}/panggil", headers=h)
    assert r.status_code == 200
    assert r.json()["status"] == "dipanggil"

    # antrian selesai tidak bisa dipanggil lagi / dibatalkan
    client.put(f"/api/visits/{v2['id']}", headers=hd, json={"diagnosa": "X", "terapi": "Y"})
    assert client.post(f"/api/antrian/{v2['id']}/panggil", headers=h).status_code == 409
    assert client.post(f"/api/antrian/{v2['id']}/batal", headers=h).status_code == 409
