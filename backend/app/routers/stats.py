from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_roles
from ..models import User, Visit
from ..redis_client import cache_get, cache_set

router = APIRouter(prefix="/stats", tags=["statistik"])

# Statistik agregat lintas dokter/staf — admin only.
# Cache Redis TTL 5 menit: data toleran delay, query group-by lumayan berat.
CACHE_KEY = "stats:overview"
CACHE_TTL = 300


def _build_overview(db: Session) -> dict:
    total_kunjungan = db.query(func.count(Visit.id)).scalar() or 0

    # Kunjungan per hari, 7 hari terakhir (isi tanggal kosong = 0 di Python)
    sejak = datetime.combine(date.today() - timedelta(days=6), datetime.min.time())
    rows = (
        db.query(func.date(Visit.created_at).label("tgl"), func.count(Visit.id))
        .filter(Visit.created_at >= sejak)
        .group_by("tgl")
        .order_by("tgl")
        .all()
    )
    by_date = {str(r[0]): r[1] for r in rows}
    kunjungan_7_hari = [
        {
            "tanggal": (sejak.date() + timedelta(days=i)).isoformat(),
            "jumlah": by_date.get((sejak.date() + timedelta(days=i)).isoformat(), 0),
        }
        for i in range(7)
    ]

    # Diagnosa terbanyak (top 10) — diagnosa free-text, grouping apa adanya
    diagnosa_terbanyak = [
        {"diagnosa": d, "jumlah": n}
        for d, n in (
            db.query(Visit.diagnosa, func.count(Visit.id))
            .filter(Visit.diagnosa.isnot(None), Visit.diagnosa != "")
            .group_by(Visit.diagnosa)
            .order_by(func.count(Visit.id).desc())
            .limit(10)
            .all()
        )
    ]

    # Dokter teraktif (top 5)
    dokter_teraktif = [
        {"nama": nama, "jumlah": n}
        for nama, n in (
            db.query(User.nama, func.count(Visit.id))
            .join(Visit, Visit.doctor_id == User.id)
            .group_by(User.id, User.nama)
            .order_by(func.count(Visit.id).desc())
            .limit(5)
            .all()
        )
    ]

    return {
        "total_kunjungan": total_kunjungan,
        "kunjungan_7_hari": kunjungan_7_hari,
        "diagnosa_terbanyak": diagnosa_terbanyak,
        "dokter_teraktif": dokter_teraktif,
    }


@router.get("/overview")
def overview(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin")),
):
    cached = cache_get(CACHE_KEY)
    if cached is not None:
        return cached
    data = _build_overview(db)
    cache_set(CACHE_KEY, data, ttl=CACHE_TTL)
    return data
