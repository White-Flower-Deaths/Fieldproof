from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="FIELDPROOF_", extra="ignore"
    )

    app_name: str = "FieldProof"
    environment: str = "development"
    database_url: str = "sqlite:///./data/fieldproof.db"

    jwt_secret: str = "dev-only-insecure-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 720

    login_max_attempts: int = 5
    login_window_seconds: int = 300

    cors_origins: str = "*"
    engine_version: str = "fp-engine-1.0.0"
    seed_demo: bool = True

    signing_key_env: str = "FIELDPROOF_SIGNING_PRIVATE_KEY"
    signing_key_file: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in {"production", "prod"}


class ImagingSettings(BaseSettings):
    """Quality gates + colour-matching thresholds (env prefix FIELDPROOF_IMAGING_)."""

    model_config = SettingsConfigDict(env_prefix="FIELDPROOF_IMAGING_", extra="ignore")

    min_width: int = 640
    min_height: int = 480
    min_blur_variance: float = 100.0
    exposure_min_mean: float = 30.0
    exposure_max_mean: float = 230.0
    glare_max_fraction: float = 0.05
    max_calibration_rms: float = 12.0
    max_delta_e: float = 15.0
    min_margin: float = 3.0


@lru_cache
def get_imaging_settings() -> ImagingSettings:
    return ImagingSettings()


imaging_settings = get_imaging_settings()


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
