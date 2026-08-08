from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_roles
from ..models import User, Visit
from ..schemas import (
    PasswordResetRequest,
    UserAdminUpdate,
    UserCreate,
    UserOut,
)
from ..security import hash_password

router = APIRouter(prefix="/users", tags=["users"])

# Semua route admin-only. Delete permanen HANYA untuk role dokter (lihat delete_user);
# admin tidak boleh dihapus permanen — pakai is_active toggle (soft delete) untuk admin.


@router.get("", response_model=list[UserOut])
def list_users(
    q: str = Query(""),
    role: str = Query(""),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin")),
):
    query = db.query(User)
    if q.strip():
        like = f"%{q.strip()}%"
        query = query.filter(
            or_(User.nama.ilike(like), User.username.ilike(like))
        )
    if role.strip():
        query = query.filter(User.role == role.strip())
    return query.order_by(User.created_at.asc(), User.id.asc()).all()


@router.post("", response_model=UserOut, status_code=201)
def create_user(
    body: UserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin")),
):
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(status_code=409, detail="Username sudah dipakai")

    user = User(
        username=body.username.strip(),
        password_hash=hash_password(body.password),
        nama=body.nama.strip(),
        role=body.role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)


@router.put("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    body: UserAdminUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles("admin")),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    if user.id == admin.id and body.is_active is False:
        raise HTTPException(status_code=400, detail="Tidak bisa menonaktifkan akun sendiri")

    data = body.model_dump(exclude_unset=True)
    if "no_sip" in data and data["no_sip"] is not None:
        data["no_sip"] = data["no_sip"].strip() or None
    for field, value in data.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)


@router.post("/{user_id}/reset-password")
def reset_password(
    user_id: int,
    body: PasswordResetRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin")),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    user.password_hash = hash_password(body.new_password)
    db.commit()
    return {"ok": True}


@router.delete("/{user_id}", status_code=204)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin")),
):
    """Hapus permanen akun. HANYA boleh untuk role 'dokter' — akun admin tidak boleh
    dihapus (cegah kehilangan akses admin), pakai is_active toggle kalau perlu."""
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    if user.role != "dokter":
        raise HTTPException(
            status_code=403,
            detail="Hanya akun dokter yang boleh dihapus — akun admin tidak bisa dihapus",
        )
    ada_riwayat = db.query(Visit).filter(Visit.doctor_id == user.id).first() is not None
    if ada_riwayat:
        raise HTTPException(
            status_code=409,
            detail="Dokter ini punya riwayat pemeriksaan pasien — tidak bisa dihapus. "
            "Nonaktifkan akunnya saja (toggle status) untuk menjaga rekam medis.",
        )
    db.delete(user)
    db.commit()
