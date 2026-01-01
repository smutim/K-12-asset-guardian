from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class School(Base):
    __tablename__ = "schools"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    users: Mapped[list["User"]] = relationship(
        back_populates="school", cascade="all, delete-orphan"
    )
    devices: Mapped[list["Device"]] = relationship(
        back_populates="school", cascade="all, delete-orphan"
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    school_id: Mapped[int] = mapped_column(
        ForeignKey("schools.id"), index=True
    )

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    school: Mapped["School"] = relationship(back_populates="users")


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    school_id: Mapped[int] = mapped_column(
        ForeignKey("schools.id"), index=True
    )

    asset_tag: Mapped[str] = mapped_column(String(100), index=True)
    serial_number: Mapped[str] = mapped_column(String(200), index=True)

    device_type: Mapped[str] = mapped_column(
        String(100), default="Chromebook"
    )

    assigned_to: Mapped[str] = mapped_column(
        String(200), default=""
    )

    status: Mapped[str] = mapped_column(
        String(50), default="unknown"
    )  # online / offline / unknown

    last_seen: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )

    battery_percent: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    school: Mapped["School"] = relationship(back_populates="devices")
    alerts: Mapped[list["Alert"]] = relationship(
        back_populates="device", cascade="all, delete-orphan"
    )


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    school_id: Mapped[int] = mapped_column(
        ForeignKey("schools.id"), index=True
    )
    device_id: Mapped[int | None] = mapped_column(
        ForeignKey("devices.id"), nullable=True
    )

    alert_type: Mapped[str] = mapped_column(
        String(100)
    )  # threshold / security / compliance

    severity: Mapped[str] = mapped_column(
        String(30), default="medium"
    )  # low / medium / high

    message: Mapped[str] = mapped_column(Text)

    acknowledged: Mapped[bool] = mapped_column(
        Boolean, default=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    device: Mapped["Device"] = relationship(back_populates="alerts")
