from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg://erm:erm@localhost:5432/erm"
    REDIS_URL: str = "redis://localhost:6379/0"
    # Tanpa default — fail-fast kalau env kosong, cegah JWT forge via secret publik
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 720
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"
    # Info klinik untuk header PDF (rekam medis & resep)
    CLINIC_NAME: str = "Klinik Sehat"
    CLINIC_ADDRESS: str = ""
    CLINIC_PHONE: str = ""
    # Password seed user pertama (dev/demo). Kosong -> random dicetak ke stdout.
    SEED_ADMIN_PASSWORD: str | None = None
    SEED_DOKTER_PASSWORD: str | None = None
    SEED_SUSTER_PASSWORD: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    def model_post_init(self, __context) -> None:
        if len(self.SECRET_KEY) < 32:
            raise ValueError(
                "SECRET_KEY minimal 32 karakter — generate dengan: python -c "
                "\"import secrets; print(secrets.token_hex(32))\""
            )

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
