from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


# ===== Auth =====
class LoginRequest(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    nama: str
    role: str
    no_sip: str | None = None
    is_active: bool = True


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=100)
    nama: str = Field(min_length=1, max_length=100)
    role: str = Field(pattern="^(admin|dokter)$")


class UserAdminUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=50)
    nama: str | None = None
    role: str | None = Field(default=None, pattern="^(admin|dokter)$")
    no_sip: str | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=6, max_length=100)


class PasswordResetRequest(BaseModel):
    new_password: str = Field(min_length=6, max_length=100)


class ProfileUpdate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    nama: str = Field(min_length=1, max_length=100)
    no_sip: str | None = None


class PasswordChange(BaseModel):
    old_password: str
    new_password: str = Field(min_length=6, max_length=100)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ===== Pasien =====
class PatientBase(BaseModel):
    nama: str = Field(min_length=1, max_length=100)
    alamat: str = ""
    jenis_identitas: str = "KTP"  # KTP | KITAS | PASSPORT
    no_identitas: str = ""
    no_hp: str = ""
    tgl_lahir: date | None = None
    pekerjaan: str = ""
    agama: str = ""
    kewarganegaraan: str = "WNI"
    status_perkawinan: str = ""
    riwayat_alergi: str = ""
    riwayat_alergi_obat: str = ""


class PatientCreate(PatientBase):
    pass


class PatientUpdate(BaseModel):
    nama: str | None = None
    alamat: str | None = None
    jenis_identitas: str | None = None
    no_identitas: str | None = None
    no_hp: str | None = None
    tgl_lahir: date | None = None
    pekerjaan: str | None = None
    agama: str | None = None
    kewarganegaraan: str | None = None
    status_perkawinan: str | None = None
    riwayat_alergi: str | None = None
    riwayat_alergi_obat: str | None = None


class PatientOut(PatientBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    no_rm: str
    usia: int | None = None
    created_at: datetime


# ===== Pemeriksaan / Visit =====
class VisitCreate(BaseModel):
    patient_id: int


class PemeriksaanUpdate(BaseModel):
    tgl_pemeriksaan: date | None = None
    anamnesa: str | None = None
    tb: float | None = None
    bb: float | None = None
    td: str | None = None
    suhu: float | None = None
    hr: int | None = None
    rr: int | None = None
    pemeriksaan_fisik: str | None = None
    diagnosa: str | None = None
    terapi: str | None = None
    surat_sakit_tgl_mulai: date | None = None
    surat_sakit_tgl_selesai: date | None = None


class VisitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    doctor_id: int | None
    antrian_no: int
    status: str
    tgl_pemeriksaan: date | None
    anamnesa: str | None
    tb: float | None
    bb: float | None
    td: str | None
    suhu: float | None
    hr: int | None
    rr: int | None
    pemeriksaan_fisik: str | None
    diagnosa: str | None
    terapi: str | None
    surat_sakit_tgl_mulai: date | None = None
    surat_sakit_tgl_selesai: date | None = None
    created_at: datetime
    updated_at: datetime
    patient: PatientOut | None = None
    doctor: UserOut | None = None


class AntrianOut(BaseModel):
    """Item antrian: visit + info pasien + dokter penanggung jawab (kalau sudah diperiksa)."""

    visit: VisitOut
    patient: PatientOut
    doctor: UserOut | None = None
