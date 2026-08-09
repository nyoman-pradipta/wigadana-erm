from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..deps import get_current_user, require_roles
from ..models import User, Visit
from ..pagination import page_params, paginate
from ..pdf import build_rekam_medis_pdf, build_resep_pdf, build_surat_sakit_pdf
from ..redis_client import cache_delete, cache_delete_prefix, cache_get, cache_set
from ..schemas import PemeriksaanUpdate, VisitOut, VisitPage

router = APIRouter(prefix="/visits", tags=["pemeriksaan"])


def _visit_query(db: Session):
    return db.query(Visit).options(
        joinedload(Visit.patient), joinedload(Visit.doctor)
    )


def _riwayat_cache_key(patient_id: int) -> str:
    return f"riwayat:{patient_id}"


@router.get("/riwayat/{patient_id}", response_model=VisitPage)
def riwayat_pasien(
    patient_id: int,
    page_pp: tuple[int, int] = Depends(page_params),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Riwayat pemeriksaan pasien, paginasi 10/halaman (list lengkap di-cache
    Redis 60 detik, invalidate saat ada update, lalu di-slice per halaman)."""
    page, per_page = page_pp
    cache_key = _riwayat_cache_key(patient_id)
    cached = cache_get(cache_key)
    if cached is not None:
        data = cached
    else:
        visits = (
            _visit_query(db)
            .filter(
                Visit.patient_id == patient_id,
                Visit.status == "selesai",
            )
            .order_by(Visit.tgl_pemeriksaan.desc(), Visit.id.desc())
            .all()
        )
        data = [VisitOut.model_validate(v).model_dump(mode="json") for v in visits]
        cache_set(cache_key, data, ttl=60)

    total = len(data)
    total_pages = max(1, (total + per_page - 1) // per_page)
    start = (page - 1) * per_page
    items = data[start : start + per_page]
    return {"items": items, "page": page, "per_page": per_page, "total": total, "total_pages": total_pages}


@router.get("/{visit_id}/pdf/rekam-medis")
def pdf_rekam_medis(
    visit_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    visit = _visit_query(db).filter(Visit.id == visit_id).first()
    if visit is None:
        raise HTTPException(status_code=404, detail="Pemeriksaan tidak ditemukan")
    pdf = build_rekam_medis_pdf(visit)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="RM-{visit.patient.no_rm}-{visit.id}.pdf"'
        },
    )


@router.get("/{visit_id}/pdf/resep")
def pdf_resep(
    visit_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    visit = _visit_query(db).filter(Visit.id == visit_id).first()
    if visit is None:
        raise HTTPException(status_code=404, detail="Pemeriksaan tidak ditemukan")
    if not (visit.terapi or "").strip():
        raise HTTPException(status_code=404, detail="Belum ada resep untuk pemeriksaan ini")
    pdf = build_resep_pdf(visit)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="Resep-{visit.patient.no_rm}-{visit.id}.pdf"'
        },
    )


@router.get("/{visit_id}/pdf/surat-sakit")
def pdf_surat_sakit(
    visit_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    visit = _visit_query(db).filter(Visit.id == visit_id).first()
    if visit is None:
        raise HTTPException(status_code=404, detail="Pemeriksaan tidak ditemukan")
    if not visit.surat_sakit_tgl_mulai or not visit.surat_sakit_tgl_selesai:
        raise HTTPException(
            status_code=404,
            detail="Isi tanggal mulai & selesai istirahat dulu untuk mencetak surat sakit",
        )
    pdf = build_surat_sakit_pdf(visit)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="SuratSakit-{visit.patient.no_rm}-{visit.id}.pdf"'
        },
    )


@router.get("/{visit_id}", response_model=VisitOut)
def get_visit(
    visit_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    visit = _visit_query(db).filter(Visit.id == visit_id).first()
    if visit is None:
        raise HTTPException(status_code=404, detail="Pemeriksaan tidak ditemukan")
    return visit


@router.put("/{visit_id}", response_model=VisitOut)
def isi_pemeriksaan(
    visit_id: int,
    body: PemeriksaanUpdate,
    db: Session = Depends(get_db),
    dokter: User = Depends(require_roles("admin", "dokter")),
):
    """Dokter mengisi hasil pemeriksaan.

    - tgl_pemeriksaan default = hari ini
    - diagnosa terisi + terapi terisi -> status 'selesai'
    - kalau masih parsial -> status 'diperiksa' (draft, bisa dilanjut)
    """
    visit = _visit_query(db).filter(Visit.id == visit_id).first()
    if visit is None:
        raise HTTPException(status_code=404, detail="Pemeriksaan tidak ditemukan")

    if dokter.role != "admin" and visit.doctor_id is not None and visit.doctor_id != dokter.id:
        raise HTTPException(
            status_code=403,
            detail="Hanya dokter yang menangani pemeriksaan ini atau admin yang boleh mengedit.",
        )

    data = body.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(visit, field, value)

    visit.doctor_id = dokter.id
    if visit.tgl_pemeriksaan is None:
        visit.tgl_pemeriksaan = date.today()

    lengkap = bool(visit.diagnosa and visit.terapi)
    visit.status = "selesai" if lengkap else "diperiksa"

    db.commit()
    db.refresh(visit)
    cache_delete(_riwayat_cache_key(visit.patient_id))
    cache_delete_prefix("antrian:")  # status berubah -> daftar antrian tidak boleh stale
    cache_delete("stats:overview")  # kunjungan bertambah
    return visit


@router.delete("/{visit_id}", status_code=204)
def hapus_visit(
    visit_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin")),
):
    """Hapus 1 riwayat pemeriksaan (visit) permanen — admin only."""
    visit = db.get(Visit, visit_id)
    if visit is None:
        raise HTTPException(status_code=404, detail="Pemeriksaan tidak ditemukan")
    patient_id = visit.patient_id
    db.delete(visit)
    db.commit()
    cache_delete(_riwayat_cache_key(patient_id))
    cache_delete_prefix("antrian:")
    cache_delete("stats:overview")
