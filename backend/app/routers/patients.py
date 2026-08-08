from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, require_roles
from ..models import Patient, User
from ..schemas import PatientCreate, PatientOut, PatientUpdate

router = APIRouter(prefix="/patients", tags=["pasien"])

# Semua role (admin, dokter) boleh baca data pasien.
# Buat/edit pasien: admin & dokter.


def _generate_no_rm(db: Session) -> str:
    """RM-000001, RM-000002, ..."""
    max_rm = db.query(func.max(Patient.no_rm)).scalar()
    if not max_rm:
        return "RM-000001"
    try:
        num = int(max_rm.split("-")[1]) + 1
    except (IndexError, ValueError):
        num = db.query(func.count(Patient.id)).scalar() + 1
    return f"RM-{num:06d}"


@router.get("", response_model=list[PatientOut])
def list_patients(
    q: str = Query("", description="Cari nama atau nomor RM"),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),  # wajib login — data pasien sensitif
):
    query = db.query(Patient)
    if q.strip():
        like = f"%{q.strip()}%"
        query = query.filter(
            or_(Patient.nama.ilike(like), Patient.no_rm.ilike(like))
        )
    return (
        query.order_by(Patient.created_at.desc(), Patient.id.desc()).limit(limit).all()
    )


@router.post("", response_model=PatientOut, status_code=201)
def create_patient(
    body: PatientCreate,
    db: Session = Depends(get_db),
    _: Patient = Depends(require_roles("admin", "dokter")),
):
    if body.no_identitas.strip():
        dupe = (
            db.query(Patient)
            .filter(
                Patient.jenis_identitas == body.jenis_identitas,
                Patient.no_identitas == body.no_identitas.strip(),
            )
            .first()
        )
        if dupe:
            raise HTTPException(
                status_code=409,
                detail=f"Nomor identitas sudah terdaftar atas nama {dupe.nama} (RM {dupe.no_rm})",
            )

    patient = Patient(
        no_rm=_generate_no_rm(db),
        nama=body.nama.strip(),
        alamat=body.alamat.strip(),
        jenis_identitas=body.jenis_identitas,
        no_identitas=body.no_identitas.strip(),
        no_hp=body.no_hp.strip(),
        tgl_lahir=body.tgl_lahir,
        pekerjaan=body.pekerjaan.strip(),
        agama=body.agama.strip(),
        kewarganegaraan=body.kewarganegaraan.strip(),
        status_perkawinan=body.status_perkawinan.strip(),
        riwayat_alergi=body.riwayat_alergi.strip(),
        riwayat_alergi_obat=body.riwayat_alergi_obat.strip(),
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


@router.get("/{patient_id}", response_model=PatientOut)
def get_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),  # wajib login — data pasien sensitif
):
    patient = db.get(Patient, patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Pasien tidak ditemukan")
    return patient


@router.put("/{patient_id}", response_model=PatientOut)
def update_patient(
    patient_id: int,
    body: PatientUpdate,
    db: Session = Depends(get_db),
    _: Patient = Depends(require_roles("admin", "dokter")),
):
    patient = db.get(Patient, patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Pasien tidak ditemukan")

    data = body.model_dump(exclude_unset=True)
    for field, value in data.items():
        if isinstance(value, str):
            value = value.strip()
        setattr(patient, field, value)
    db.commit()
    db.refresh(patient)
    return patient
