from datetime import datetime
from sqlalchemy import (
    String,
    Integer,
    DateTime,
    ForeignKey,
    Boolean,
    Text,
    JSON,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class ExternalDeviceId(Base):
    """
    Maps your internal Device record to external systems:
    - google (Chromebook deviceId)
    - intune (managedDeviceId)
    - jamf (jamfId)
    """
    __tablename__ = "external_device_ids"
    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_source_external_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), index=True)

    source: Mapped[str] = mapped_column(String(50), index=True)
    external_id: Mapped[str] = mapped_column(String(255), index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class DeviceNetworkIdentity(Base):
    """
    Tracks identifiers used for correlating firewall/webfilter logs to devices.
    """
    __tablename__ = "device_network_identities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), index=True)

    mac: Mapped[str] = mapped_column(String(50), index=True)
    hostname: Mapped[str] = mapped_column(String(255), default="")
    last_ip: Mapped[str] = mapped_column(String(50), default="")
    last_seen: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Event(Base):
    """
    Normalized event stream across sources:
    - google inventory sync
    - goguardian web_access
    - sonicwall web_access
    - dns query
    - compliance changes, etc.
    """
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), index=True)
    device_id: Mapped[int | None] = mapped_column(ForeignKey("devices.id"), nullable=True, index=True)

    event_type: Mapped[str] = mapped_column(String(80), index=True)
    severity: Mapped[str] = mapped_column(String(30), default="info")  # info/low/medium/high
    source: Mapped[str] = mapped_column(String(80), default="")        # google/sonicwall/goguardian/...

    message: Mapped[str] = mapped_column(Text, default="")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetim]()_
