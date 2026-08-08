from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import User
from ..redis_client import cache_delete, rate_limit_exceeded
from ..schemas import (
    LoginRequest,
    PasswordChange,
    ProfileUpdate,
    TokenResponse,
    UserOut,
)
from ..security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

# 5 percobaan login gagal per 15 menit per IP+username (Redis; fallback: tanpa limit)
_LOGIN_LIMIT = 5
_LOGIN_WINDOW = 15 * 60


def _login_key(request: Request, username: str) -> str:
    ip = request.client.host if request.client else "unknown"
    return f"login_fail:{ip}:{username}"


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    key = _login_key(request, body.username)
    if rate_limit_exceeded(key, _LOGIN_LIMIT, _LOGIN_WINDOW):
        raise HTTPException(
            status_code=429,
            detail="Terlalu banyak percobaan login. Coba lagi 15 menit lagi.",
        )

    user = db.query(User).filter(User.username == body.username).first()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Username atau password salah")
    if not user.is_active:
        raise HTTPException(status_code=401, detail="Akun dinonaktifkan")

    cache_delete(key)  # login sukses -> reset counter percobaan
    token = create_access_token(user.id, user.role, user.nama)
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return UserOut.model_validate(user)


@router.put("/me", response_model=UserOut)
def update_profil(
    body: ProfileUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Edit nama & no. SIP sendiri. Identitas dari token (bukan path param) — anti IDOR."""
    user.nama = body.nama.strip()
    if body.no_sip is not None:
        user.no_sip = body.no_sip.strip() or None
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)


@router.post("/me/password")
def ganti_password(
    body: PasswordChange,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not verify_password(body.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Password lama salah")
    user.password_hash = hash_password(body.new_password)
    db.commit()
    return {"ok": True}
