from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    nama: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(20), default="dokter")  # admin | dokter
    no_sip: Mapped[str | None] = mapped_column(String(50), nullable=True)  # nomor SIP dokter (resep)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(primary_key=True)
    no_rm: Mapped[str] = mapped_column(String(20), unique=True, index=True)  # nomor ID klinik
    nama: Mapped[str] = mapped_column(String(100), index=True)
    alamat: Mapped[str] = mapped_column(Text, default="")
    jenis_identitas: Mapped[str] = mapped_column(String(20), default="KTP")  # KTP | KITAS | PASSPORT
    no_identitas: Mapped[str] = mapped_column(String(50), default="")
    no_hp: Mapped[str] = mapped_column(String(20), default="")
    tgl_lahir: Mapped[date | None] = mapped_column(Date, nullable=True)  # untuk hitung usia otomatis
    pekerjaan: Mapped[str] = mapped_column(String(100), default="")  # untuk surat sakit
    agama: Mapped[str] = mapped_column(String(30), default="")
    kewarganegaraan: Mapped[str] = mapped_column(String(30), default="WNI")
    status_perkawinan: Mapped[str] = mapped_column(String(20), default="")  # Belum Menikah | Menikah | Cerai
    riwayat_alergi: Mapped[str] = mapped_column(Text, default="")
    riwayat_alergi_obat: Mapped[str] = mapped_column(Text, default="")  # WAJIB tampil sebelum anamnesis
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    @property
    def usia(self) -> int | None:
        """Usia dalam tahun, dihitung dari tgl_lahir (bukan disimpan — selalu akurat)."""
        if self.tgl_lahir is None:
            return None
        today = date.today()
        years = today.year - self.tgl_lahir.year
        if (today.month, today.day) < (self.tgl_lahir.month, self.tgl_lahir.day):
            years -= 1
        return years

    visits: Mapped[list["Visit"]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )


class Visit(Base):
    __tablename__ = "visits"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    doctor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    antrian_no: Mapped[int] = mapped_column(Integer, index=True)
    # menunggu -> dipanggil -> diperiksa -> selesai
    status: Mapped[str] = mapped_column(String(20), default="menunggu", index=True)

    # ===== data pemeriksaan =====
    tgl_pemeriksaan: Mapped[date | None] = mapped_column(Date, nullable=True)
    anamnesa: Mapped[str | None] = mapped_column(Text, nullable=True)
    tb: Mapped[float | None] = mapped_column(Float, nullable=True)  # tinggi badan (cm)
    bb: Mapped[float | None] = mapped_column(Float, nullable=True)  # berat badan (kg)
    td: Mapped[str | None] = mapped_column(String(15), nullable=True)  # tekanan darah "120/80"
    suhu: Mapped[float | None] = mapped_column(Float, nullable=True)  # celsius
    hr: Mapped[int | None] = mapped_column(Integer, nullable=True)  # nadi /menit
    rr: Mapped[int | None] = mapped_column(Integer, nullable=True)  # napas /menit
    pemeriksaan_fisik: Mapped[str | None] = mapped_column(Text, nullable=True)
    diagnosa: Mapped[str | None] = mapped_column(Text, nullable=True)
    terapi: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ===== surat keterangan sakit (opsional, diisi kalau pasien minta) =====
    surat_sakit_tgl_mulai: Mapped[date | None] = mapped_column(Date, nullable=True)
    surat_sakit_tgl_selesai: Mapped[date | None] = mapped_column(Date, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    patient: Mapped[Patient] = relationship(back_populates="visits")
    doctor: Mapped[User | None] = relationship()
