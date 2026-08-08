import logging
import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import Base, SessionLocal, engine
from .models import Patient, User, Visit  # noqa: F401  (registrasi tabel)
from .redis_client import REDIS_OK
from .routers import antrian, auth, patients, stats, users, visits
from .security import hash_password

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _seed_default_users() -> None:
    """User awal. Password: dari settings.SEED_*_PASSWORD (env atau .env) kalau ada,
    kalau tidak random (dicetak sekali ke stdout). Wajib ganti setelah login pertama."""
    db = SessionLocal()
    try:
        if db.query(User).count() > 0:
            return
        seed_pw = {
            "admin": settings.SEED_ADMIN_PASSWORD,
            "wigadana": settings.SEED_DOKTER_PASSWORD,
        }
        defaults = [
            ("admin", "Administrator", "admin"),
            ("wigadana", "Dr. Andini", "dokter"),
        ]
        created = []
        for username, nama, role in defaults:
            pw = seed_pw.get(username) or secrets.token_urlsafe(9)
            db.add(User(username=username, password_hash=hash_password(pw), nama=nama, role=role))
            created.append((username, pw))
        db.commit()
        for username, pw in created:
            if seed_pw.get(username):
                continue
            print(f"[seed] user '{username}' dibuat dengan password acak: {pw} — GANTI setelah login!", flush=True)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    _seed_default_users()
    logger.info(
        "ERM Klinik siap — Redis: %s | DB: %s",
        "OK" if REDIS_OK else "OFFLINE (fallback DB)",
        settings.DATABASE_URL.split("://")[0],
    )
    yield


app = FastAPI(
    title="ERM Klinik API",
    description="Sistem Rekam Medis Elektronik sederhana untuk klinik",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "same-origin"
    return resp

app.include_router(auth.router, prefix="/api")
app.include_router(patients.router, prefix="/api")
app.include_router(antrian.router, prefix="/api")
app.include_router(visits.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(stats.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok", "redis": REDIS_OK}
