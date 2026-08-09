from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..deps import get_current_user, require_roles
from ..models import Patient, User, Visit
from ..pagination import page_params, paginate
from ..redis_client import (
    cache_delete_prefix,
    cache_get,
    cache_set,
    next_antrian_counter,
)
from ..schemas import AntrianOut, AntrianPage, PatientOut, UserOut, VisitCreate, VisitOut

router = APIRouter(prefix="/antrian", tags=["antrian"])

_ACTIVE_STATUS = ("menunggu", "dipanggil", "diperiksa")
CACHE_PREFIX = "antrian:"


def _visit_query(db: Session):
    return db.query(Visit).options(
        joinedload(Visit.patient), joinedload(Visit.doctor)
    )


def _serialize(visits: list[Visit]) -> list[dict]:
    """Dict JSON-safe (primitif murni) — wajib, karena hasilnya di-cache ke Redis
    via json.dumps. Objek ORM mentah (Patient/User) tidak JSON-serializable dan
    akan corrupt jadi string saat di-cache, bikin 500 di request berikutnya."""
    return [
        {
            "visit": VisitOut.model_validate(v).model_dump(mode="json"),
            "patient": PatientOut.model_validate(v.patient).model_dump(mode="json"),
            "doctor": UserOut.model_validate(v.doctor).model_dump(mode="json") if v.doctor else None,
        }
        for v in visits
    ]


def _antrian_counter_key() -> str:
    return f"antrian:counter:{date.today().isoformat()}"


def _next_no_from_db(db: Session) -> int:
    """Fallback nomor antrian dari DB (per hari)."""
    today = date.today()
    max_no = (
        db.query(func.max(Visit.antrian_no))
        .filter(func.date(Visit.created_at) == today)
        .scalar()
    )
    return (max_no or 0) + 1


@router.post("", response_model=VisitOut, status_code=201)
def daftar_antrian(
    body: VisitCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "dokter")),
):
    """Pasien daftar -> dapat nomor antrian (counter Redis per hari, fallback DB)."""
    patient = db.get(Patient, body.patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Pasien tidak ditemukan")

    # Cegah daftar dobel kalau masih ada antrian aktif
    aktif = (
        db.query(Visit)
        .filter(Visit.patient_id == body.patient_id, Visit.status.in_(_ACTIVE_STATUS))
        .first()
    )
    if aktif:
        raise HTTPException(
            status_code=409,
            detail=f"Pasien masih punya antrian aktif (nomor {aktif.antrian_no})",
        )

    no = next_antrian_counter(_antrian_counter_key())
    if no is None:
        no = _next_no_from_db(db)

    visit = Visit(patient_id=body.patient_id, antrian_no=no, status="menunggu")
    db.add(visit)
    db.commit()
    db.refresh(visit)

    cache_delete_prefix(CACHE_PREFIX)
    return visit


@router.get("", response_model=AntrianPage)
def list_antrian(
    status: str = Query("aktif", description="aktif | menunggu | dipanggil | diperiksa | selesai"),
    page_pp: tuple[int, int] = Depends(page_params),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Daftar antrian (paginasi 10/halaman). Default: semua yang belum selesai
    (list lengkap di-cache Redis 30 detik, lalu di-slice per halaman)."""
    page, per_page = page_pp
    cache_key = f"{CACHE_PREFIX}list:{status}"
    cached = cache_get(cache_key)
    if cached is not None:
        data = cached
    else:
        query = _visit_query(db)
        if status == "aktif":
            query = query.filter(Visit.status.in_(_ACTIVE_STATUS))
        else:
            query = query.filter(Visit.status == status)

        visits = query.order_by(Visit.antrian_no.asc()).all()
        data = _serialize(visits)
        cache_set(cache_key, data, ttl=30)

    total = len(data)
    total_pages = max(1, (total + per_page - 1) // per_page)
    start = (page - 1) * per_page
    items = data[start : start + per_page]
    return {"items": items, "page": page, "per_page": per_page, "total": total, "total_pages": total_pages}


@router.get("/saat-ini", response_model=AntrianOut | None)
def antrian_saat_ini(
    db: Session = Depends(get_db), _: User = Depends(get_current_user)
):
    """Nomor antrian yang sedang dipanggil (paling baru)."""
    visit = (
        _visit_query(db)
        .filter(Visit.status == "dipanggil")
        .order_by(Visit.updated_at.desc())
        .first()
    )
    if visit is None:
        return None
    return {
        "visit": VisitOut.model_validate(visit).model_dump(mode="json"),
        "patient": PatientOut.model_validate(visit.patient).model_dump(mode="json"),
        "doctor": UserOut.model_validate(visit.doctor).model_dump(mode="json") if visit.doctor else None,
    }


@router.post("/{visit_id}/panggil", response_model=VisitOut)
def panggil(
    visit_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "dokter")),
):
    """Suster manggil pasien sesuai antrian -> status dipanggil.

    Boleh dari 'menunggu' (normal) atau 'diperiksa' (panggil ulang draft).
    """
    visit = _visit_query(db).filter(Visit.id == visit_id).first()
    if visit is None:
        raise HTTPException(status_code=404, detail="Antrian tidak ditemukan")
    if visit.status not in ("menunggu", "diperiksa"):
        raise HTTPException(
            status_code=409,
            detail=f"Antrian berstatus '{visit.status}' — tidak bisa dipanggil",
        )

    visit.status = "dipanggil"
    db.commit()
    db.refresh(visit)
    cache_delete_prefix(CACHE_PREFIX)
    return visit


@router.post("/{visit_id}/batal", response_model=VisitOut)
def batal(
    visit_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "dokter")),
):
    """Batalkan antrian (salah panggil, pasien batal tunggu, draft ditinggalkan)."""
    visit = _visit_query(db).filter(Visit.id == visit_id).first()
    if visit is None:
        raise HTTPException(status_code=404, detail="Antrian tidak ditemukan")
    if visit.status == "selesai":
        raise HTTPException(status_code=409, detail="Antrian sudah selesai")

    visit.status = "batal"
    db.commit()
    db.refresh(visit)
    cache_delete_prefix(CACHE_PREFIX)
    return visit
