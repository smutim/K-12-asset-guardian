from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


# ----------------------------
# Core Models
# ----------------------------

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class School(Base):
    __tablename__ = "schools"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)

    # Optional metadata / identifiers
    district: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    customer_code: Mapped[Optional[str]] = mapped_column(String(100), unique=True, index=True, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    devices: Mapped[list["Device"]] = relationship(
        "Device",
        back_populates="school",
        cascade="all, delete-orphan",
    )

    api_keys: Mapped[list["SchoolApiKey"]] = relationship(
        "SchoolApiKey",
        back_populates="school",
        cascade="all, delete-orphan",
    )

    events: Mapped[list["Event"]] = relationship(
        "Event",
        back_populates="school",
        cascade="all, delete-orphan",
    )


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    school_id: Mapped[int] = mapped_column(Integer, ForeignKey("schools.id"), nullable=False, index=True)

    # Identifiers
    asset_tag: Mapped[Optional[str]] = mapped_column(String(100), index=True, nullable=True)
    serial_number: Mapped[Optional[str]] = mapped_column(String(128), index=True, nullable=True)
    device_name: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)

    # State / health
    status: Mapped[Optional[str]] = mapped_column(String(50), index=True, nullable=True)  # e.g. active, lost, retired
    is_online: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    last_seen: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    school: Mapped["School"] = relationship("School", back_populates="devices")

    alerts: Mapped[list["Alert"]] = relationship(
        "Alert",
        back_populates="device",
        cascade="all, delete-orphan",
    )

    network_identities: Mapped[list["DeviceNetworkIdentity"]] = relationship(
        "DeviceNetworkIdentity",
        back_populates="device",
        cascade="all, delete-orphan",
    )

    external_ids: Mapped[list["ExternalDeviceId"]] = relationship(
        "ExternalDeviceId",
        back_populates="device",
        cascade="all, delete-orphan",
    )

    events: Mapped[list["Event"]] = relationship(
        "Event",
        back_populates="device",
        cascade="all, delete-orphan",
    )


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    device_id: Mapped[int] = mapped_column(Integer, ForeignKey("devices.id"), nullable=False, index=True)

    # Alert details
    severity: Mapped[str] = mapped_column(String(20), index=True, nullable=False)  # e.g. low/medium/high
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    device: Mapped["Device"] = relationship("Device", back_populates="alerts")


# ----------------------------
# Extended / Ingestion Models
# (moved here to eliminate duplication issues)
# ----------------------------

class SchoolApiKey(Base):
    __tablename__ = "school_api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    school_id: Mapped[int] = mapped_column(Integer, ForeignKey("schools.id"), nullable=False, index=True)

    # Store only hashed keys in production; for now keep as plain string if you must.
    key: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)

    label: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    school: Mapped["School"] = relationship("School", back_populates="api_keys")


class ExternalDeviceId(Base):
    """
    External system identifier for a device.
    Example: Google Admin deviceId, GoGuardian device id, Jamf id, etc.
    """
    __tablename__ = "external_device_ids"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    device_id: Mapped[int] = mapped_column(Integer, ForeignKey("devices.id"), nullable=False, index=True)

    source: Mapped[str] = mapped_column(String(50), index=True, nullable=False)  # google_chrome, goguardian, jamf
    external_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    device: Mapped["Device"] = relationship("Device", back_populates="external_ids")


class DeviceNetworkIdentity(Base):
    """
    Network identity info for a device (IP/MAC/hostname/source system, etc.)
    """
    __tablename__ = "device_network_identities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    device_id: Mapped[int] = mapped_column(Integer, ForeignKey("devices.id"), nullable=False, index=True)

    source: Mapped[str] = mapped_column(String(50), index=True, nullable=False)  # goguardian, google, jamf
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)  # IPv4/IPv6 max length 45
    mac_address: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    hostname: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    last_seen: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    device: Mapped["Device"] = relationship("Device", back_populates="network_identities")


class Event(Base):
    """
    Generic event/telemetry ingestion table.
    Store payload as text to keep DB simple (SQLite/Postgres friendly).
    """
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    school_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("schools.id"), nullable=True, index=True)
    device_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("devices.id"), nullable=True, index=True)

    source: Mapped[str] = mapped_column(String(50), index=True, nullable=False)  # goguardian, google_chrome, manual
    event_type: Mapped[str] = mapped_column(String(100), index=True, nullable=False)

    payload: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    school: Mapped[Optional["School"]] = relationship("School", back_populates="events")
    device: Mapped[Optional["Device"]] = relationship("Device", back_populates="events")


class PolicyRule(Base):
    """
    Policy engine rules to evaluate incoming events.
    Keep this minimal and evolve as your engine matures.
    """
    __tablename__ = "policy_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Matching logic
    source: Mapped[Optional[str]] = mapped_column(String(50), index=True, nullable=True)
    event_type: Mapped[Optional[str]] = mapped_column(String(100), index=True, nullable=True)

    # Simple rule expression / action (store as text for now)
    condition: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    action: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
