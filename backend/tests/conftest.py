"""Test fixtures — sqlite temp + Redis mati (fallback), supaya test jalan tanpa infra."""
import os
import shutil
import tempfile

# Set env SEBELUM import app (config.py baca env saat import)
_tmp = tempfile.mkdtemp(prefix="erm-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/erm_test.db"
os.environ["REDIS_URL"] = "redis://127.0.0.1:6399/0"  # port kosong -> REDIS_OK=False
os.environ["SECRET_KEY"] = "test-secret-yang-panjang-untuk-hmac-32-byte"
# Seed user deterministik supaya test bisa login
os.environ["SEED_ADMIN_PASSWORD"] = "123456"
os.environ["SEED_DOKTER_PASSWORD"] = "123456"

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:  # lifespan: create_all + seed user default
        yield c
    shutil.rmtree(_tmp, ignore_errors=True)


@pytest.fixture(scope="session")
def dokter_token(client):
    r = client.post("/api/auth/login", json={"username": "wigadana", "password": "123456"})
    assert r.status_code == 200
    return r.json()["access_token"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
