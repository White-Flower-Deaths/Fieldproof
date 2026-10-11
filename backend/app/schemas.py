from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --------------------------------------------------------------------------- auth
class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class RegisterRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1)


class UserOut(ORMModel):
    id: str
    username: str
    full_name: str
    badge_number: str | None = None
    role: Literal["OFFICER", "LAB", "ADMIN"]
    agency: str | None = None
    is_active: bool
    last_login_at: datetime | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


class MessageOut(BaseModel):
    detail: str


# --------------------------------------------------------------------------- meta
class MetaOut(BaseModel):
    app_name: str
    environment: str
    engine_version: str
    disclaimer: str
    concentration_note: str
    roles: list[str]
    appearance_options: list[str]
    test_types: list[str]
    result_statuses: list[str]
    demo_mode_default: bool


class KitOutcomeOut(BaseModel):
    code: str
    label: str
    hex: str | None = None
    interpretation: str | None = None
    sort_order: int = 0


class KitOut(BaseModel):
    code: str
    name: str
    test_type: str
    manufacturer: str | None = None
    description: str | None = None
    instructions: str | None = None
    reaction_time_seconds: int | None = None
    requires_photo: bool = False
    is_demo: bool = False
    source_citation: str
    outcomes: list[KitOutcomeOut] = []


# --------------------------------------------------------------------------- samples
_HEX64 = r"^[0-9a-fA-F]{64}$"


class SampleCreate(BaseModel):
    appearance: Literal[
        "POWDER", "CRYSTALS", "PILL_TABLET", "PLANT_MATERIAL", "BLOTTER",
        "LIQUID", "OTHER",
    ] = "POWDER"
    colour: str | None = Field(default=None, max_length=64)
    approximate_weight: str | None = Field(default=None, max_length=32)
    notes: str | None = Field(default=None, max_length=4000)
    photo_sha256: str | None = Field(default=None, pattern=_HEX64)
    gps_lat: float | None = Field(default=None, ge=-90, le=90)
    gps_lon: float | None = Field(default=None, ge=-180, le=180)
    gps_accuracy_m: float | None = Field(default=None, ge=0)
    gps_mock_location: bool = False
    device_timestamp: datetime | None = None


class SampleTestOut(ORMModel):
    id: str
    test_type: str
    kit_code: str | None = None
    kit_name: str | None = None
    kit_batch: str | None = None
    outcome_code: str | None = None
    outcome_label: str | None = None
    input_json: dict[str, Any] = {}
    time_since_reaction_seconds: int | None = None
    image_sha256: str | None = None
    source: str = "MANUAL"
    is_override: bool = False
    override_reason: str | None = None
    overridden_outcome_code: str | None = None
    created_at: datetime


class SampleOut(ORMModel):
    id: str
    sample_code: str
    operator_id: str
    operator_username: str | None = None
    appearance: str
    colour: str | None = None
    approximate_weight: str | None = None
    notes: str | None = None
    photo_sha256: str | None = None
    gps_lat: float | None = None
    gps_lon: float | None = None
    gps_accuracy_m: float | None = None
    gps_mock_location: bool = False
    device_timestamp: datetime | None = None
    status: str
    created_at: datetime
    updated_at: datetime
    tests: list[SampleTestOut] = []


class TestCreate(BaseModel):
    test_type: Literal[
        "COLOUR_REAGENT", "IMMUNOASSAY_STRIP", "SPECTROMETER", "LAB_CONFIRMATORY"
    ]
    kit_code: str | None = Field(default=None, max_length=48)
    kit_batch: str | None = Field(default=None, max_length=48)
    outcome_code: str | None = Field(default=None, max_length=48)
    time_since_reaction_seconds: int | None = Field(default=None, ge=0, le=86400)
    image_sha256: str | None = Field(default=None, pattern=_HEX64)
    source: Literal["MANUAL", "CAMERA"] = "MANUAL"
    input: dict[str, Any] = Field(default_factory=dict)
    calibration: dict[str, Any] | None = None
    reading: dict[str, Any] | None = None
    is_override: bool = False
    override_reason: str | None = Field(default=None, max_length=1000)
    overridden_outcome_code: str | None = Field(default=None, max_length=48)


class TestCreateOut(BaseModel):
    test: SampleTestOut
    analysis: dict[str, Any]


# --------------------------------------------------------------------------- records
class RecordSummary(BaseModel):
    id: str
    sample_id: str
    sample_code: str
    status: str
    operator_id: str
    operator_username: str | None = None
    operator_badge: str | None = None
    kit_codes: list[str] = []
    top_substance_code: str | None = None
    top_substance_name: str | None = None
    server_timestamp: datetime
    record_hash: str
    previous_record_hash: str | None = None
    public_key_id: str | None = None
    gps_lat: float | None = None
    gps_lon: float | None = None
    gps_accuracy_m: float | None = None
    gps_mock_location: bool = False
    image_sha256: str | None = None
    engine_version: str
    disclaimer: str


class RecordListOut(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[RecordSummary]


# --------------------------------------------------------------------------- analysis
class ObservationIn(BaseModel):
    ref: str | None = None
    test_type: Literal[
        "COLOUR_REAGENT", "IMMUNOASSAY_STRIP", "SPECTROMETER", "LAB_CONFIRMATORY"
    ]
    kit_id: str | None = None
    kit_code: str = ""
    kit_name: str = ""
    outcome_code: str | None = None
    outcome_label: str | None = None
    inconclusive: bool = False
    kit_batch: str | None = None
    library_match: str | None = None
    match_score: float | None = Field(default=None, ge=0, le=100)
    lab_method: str | None = None
    lab_compound: str | None = None
    lab_reference: str | None = None
    purity_percent: float | None = Field(default=None, ge=0, le=100)


class AnalysisPreviewIn(BaseModel):
    observations: list[ObservationIn] = Field(default_factory=list)


class AnalysisOut(BaseModel):
    result: dict[str, Any]


# --------------------------------------------------------------------------- health
class HealthOut(BaseModel):
    status: str
    database: str
    version: str
    time: datetime


class ErrorOut(BaseModel):
    detail: str | Any = None
