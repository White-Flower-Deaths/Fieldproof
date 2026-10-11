"""SQLAlchemy models. Schema is portable to PostgreSQL (no SQLite-only types)."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    event,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base, utcnow


def new_uuid() -> str:
    return str(uuid.uuid4())


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow, nullable=False
    )


# --------------------------------------------------------------------------- #
# users
# --------------------------------------------------------------------------- #
class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    badge_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="OFFICER")
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    agency: Mapped[str | None] = mapped_column(String(120), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    samples: Mapped[list["Sample"]] = relationship(back_populates="operator")


# --------------------------------------------------------------------------- #
# samples
# --------------------------------------------------------------------------- #
class Sample(Base, TimestampMixin):
    __tablename__ = "samples"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    sample_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    operator_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    appearance: Mapped[str] = mapped_column(String(24), nullable=False, default="POWDER")
    colour: Mapped[str | None] = mapped_column(String(64), nullable=True)
    approximate_weight: Mapped[str | None] = mapped_column(String(32), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    photo_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    photo_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    gps_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    gps_lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    gps_accuracy_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    gps_mock_location: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    device_timestamp: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="DRAFT", nullable=False)

    operator: Mapped[User] = relationship(back_populates="samples")
    tests: Mapped[list["SampleTest"]] = relationship(
        back_populates="sample", cascade="all, delete-orphan"
    )

    @property
    def operator_username(self) -> str | None:
        return self.operator.username if self.operator is not None else None


# --------------------------------------------------------------------------- #
# reference data: substances, kits (table "tests"), outcomes, reactions
# --------------------------------------------------------------------------- #
class Substance(Base, TimestampMixin):
    __tablename__ = "substances"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    aliases: Mapped[list] = mapped_column(JSON, default=list)
    substance_class: Mapped[str | None] = mapped_column(String(80), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    source_citation: Mapped[str] = mapped_column(Text, nullable=False)

    reactions: Mapped[list["ExpectedReaction"]] = relationship(back_populates="substance")


class Kit(Base, TimestampMixin):
    """A kit / test definition. Maps to the `tests` table."""

    __tablename__ = "tests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(48), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    test_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    manufacturer: Mapped[str | None] = mapped_column(String(120), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    reaction_time_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    requires_photo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    source_citation: Mapped[str] = mapped_column(Text, nullable=False)

    outcomes: Mapped[list["TestOutcome"]] = relationship(
        back_populates="kit", cascade="all, delete-orphan", order_by="TestOutcome.sort_order"
    )
    reactions: Mapped[list["ExpectedReaction"]] = relationship(back_populates="kit")


class TestOutcome(Base, TimestampMixin):
    __tablename__ = "test_outcomes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    kit_id: Mapped[str] = mapped_column(ForeignKey("tests.id"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(48), nullable=False)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    hex: Mapped[str | None] = mapped_column(String(7), nullable=True)
    # Reference Lab colour of the reaction as published by the kit maker.
    ref_l: Mapped[float | None] = mapped_column(Float, nullable=True)
    ref_a: Mapped[float | None] = mapped_column(Float, nullable=True)
    ref_b: Mapped[float | None] = mapped_column(Float, nullable=True)
    interpretation: Mapped[str | None] = mapped_column(Text, nullable=True)
    cross_reactions: Mapped[list] = mapped_column(JSON, default=list)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    source_citation: Mapped[str] = mapped_column(Text, nullable=False)

    kit: Mapped[Kit] = relationship(back_populates="outcomes")

    __table_args__ = (UniqueConstraint("kit_id", "code", name="uq_outcome_kit_code"),)


class ExpectedReaction(Base, TimestampMixin):
    __tablename__ = "expected_reactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    substance_id: Mapped[str] = mapped_column(ForeignKey("substances.id"), nullable=False)
    kit_id: Mapped[str] = mapped_column(ForeignKey("tests.id"), nullable=False)
    outcome_id: Mapped[str] = mapped_column(ForeignKey("test_outcomes.id"), nullable=False)
    likelihood: Mapped[float] = mapped_column(Float, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    source_citation: Mapped[str] = mapped_column(Text, nullable=False)

    substance: Mapped[Substance] = relationship(back_populates="reactions")
    kit: Mapped[Kit] = relationship(back_populates="reactions")
    outcome: Mapped[TestOutcome] = relationship()

    __table_args__ = (
        UniqueConstraint(
            "substance_id", "kit_id", "outcome_id", "version", name="uq_reaction_row"
        ),
    )


# --------------------------------------------------------------------------- #
# per-sample tests (the officer's entries)
# --------------------------------------------------------------------------- #
class SampleTest(Base, TimestampMixin):
    __tablename__ = "sample_tests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    sample_id: Mapped[str] = mapped_column(ForeignKey("samples.id"), nullable=False, index=True)
    # nullable: LAB_CONFIRMATORY and spectrometer entries may have no kit row
    kit_id: Mapped[str | None] = mapped_column(ForeignKey("tests.id"), nullable=True, index=True)
    operator_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    test_type: Mapped[str] = mapped_column(String(32), nullable=False)
    kit_batch: Mapped[str | None] = mapped_column(String(48), nullable=True)
    outcome_id: Mapped[str | None] = mapped_column(ForeignKey("test_outcomes.id"), nullable=True)
    outcome_code: Mapped[str | None] = mapped_column(String(48), nullable=True)
    outcome_label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # Free-form typed input for strip / spectrometer / lab entries.
    input_json: Mapped[dict] = mapped_column(JSON, default=dict)
    time_since_reaction_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    image_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    image_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    calibration_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    reading_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    source: Mapped[str] = mapped_column(String(16), default="MANUAL", nullable=False)
    is_override: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    overridden_outcome_code: Mapped[str | None] = mapped_column(String(48), nullable=True)

    sample: Mapped[Sample] = relationship(back_populates="tests")
    kit: Mapped[Kit | None] = relationship()
    outcome: Mapped[TestOutcome | None] = relationship()

    @property
    def kit_code(self) -> str | None:
        return self.kit.code if self.kit else None

    @property
    def kit_name(self) -> str | None:
        return self.kit.name if self.kit else None


# --------------------------------------------------------------------------- #
# records (append-only, hash-chained, signed)
# --------------------------------------------------------------------------- #
class Record(Base):
    __tablename__ = "records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    sample_id: Mapped[str] = mapped_column(ForeignKey("samples.id"), nullable=False, index=True)
    operator_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)

    kit_codes: Mapped[list] = mapped_column(JSON, default=list)
    kit_batches: Mapped[list] = mapped_column(JSON, default=list)
    # denormalised for portable SQL filtering
    kit_codes_csv: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    top_substance_code: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    top_substance_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    test_inputs: Mapped[list] = mapped_column(JSON, default=list)
    analysis: Mapped[dict] = mapped_column(JSON, default=dict)
    calibration: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    gps_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    gps_lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    gps_accuracy_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    gps_mock_location: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    device_timestamp: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    server_timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    image_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    previous_record_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    record_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # Exact bytes that were hashed and signed (canonical JSON, sorted keys).
    canonical_json: Mapped[str] = mapped_column(Text, nullable=False)
    signature: Mapped[str | None] = mapped_column(Text, nullable=True)
    public_key_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    engine_version: Mapped[str] = mapped_column(String(32), nullable=False)
    disclaimer: Mapped[str] = mapped_column(Text, nullable=False)

    correction_of: Mapped[str | None] = mapped_column(String(36), nullable=True)
    superseded_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


@event.listens_for(Record, "before_update")
def _records_append_only_update(mapper, connection, target):  # pragma: no cover
    raise RuntimeError("records are append-only: create a correction record instead")


@event.listens_for(Record, "before_delete")
def _records_append_only_delete(mapper, connection, target):  # pragma: no cover
    raise RuntimeError("records are append-only: deletion is not permitted")


# --------------------------------------------------------------------------- #
# audit + signing keys
# --------------------------------------------------------------------------- #
class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    actor_username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    actor_role: Mapped[str | None] = mapped_column(String(16), nullable=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_type: Mapped[str | None] = mapped_column(String(48), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, nullable=False, index=True
    )


class SigningKey(Base):
    __tablename__ = "signing_keys"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    key_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    algorithm: Mapped[str] = mapped_column(String(32), default="ECDSA-P256-SHA256")
    public_key_pem: Mapped[str] = mapped_column(Text, nullable=False)
    # Where the PRIVATE half lives (env var name or file path). Never the key itself.
    private_key_source: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    retired_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
