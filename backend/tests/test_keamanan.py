"""Test keamanan — hasil audit (Claude Code): endpoint pasien wajib login, headers."""
from conftest import auth


def test_pasien_wajib_login(client):
    """Sebelum fix: GET /patients & /patients/{id} terbuka tanpa token (data pasien bocor)."""
    assert client.get("/api/patients").status_code == 401
    assert client.get("/api/patients/1").status_code == 401


def test_pasien_bisa_diakses_setelah_login(client, dokter_token):
    h = auth(dokter_token)
    p = client.post("/api/patients", headers=h, json={"nama": "Rahasia", "no_hp": "0811"}).json()
    assert client.get("/api/patients", headers=h).status_code == 200
    assert client.get(f"/api/patients/{p['id']}", headers=h).status_code == 200
    assert client.get(f"/api/patients/{p['id']}").status_code == 401


def test_security_headers(client):
    r = client.get("/api/health")
    assert r.headers.get("x-content-type-options") == "nosniff"
    assert r.headers.get("x-frame-options") == "DENY"
    assert r.headers.get("referrer-policy") == "same-origin"
