from datetime import datetime
from pydantic import BaseModel, EmailStr


# -------------------------
# Schools
# -------------------------
class SchoolCreate(BaseModel):
    name: str


class SchoolOut(BaseModel):
    id: int
    name: str
    created_at: datetime

    class Config:
        from_attributes = True


# -------------------------
# Users / Auth
# -------------------------
class UserCreate(BaseModel):
    school_id: int
    email: EmailStr
    password: str
    is_admin: bool = False


class UserOut(BaseModel):
    id: int
    school_id: int
    email: EmailStr
    is_admin: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


# -------------------------
# Devices
# -------------------------
class DeviceCreate(BaseModel):
    school_id: int
    asset_tag: str
    serial_number: str
    device_type: str = "Chromebook"
    assigned_to: str = ""


class DeviceOut(BaseModel):
    id: int
    school_id: int
    asset_tag: str
    serial_number: str
    device_type: str
    assigned_to: str
    status: str
    last_seen: datetime | None
    battery_percent: int | None
    created_at: datetime

    class Config:
        from_attributes = True


# -------------------------
# Alerts
# -------------------------
class AlertOut(BaseModel):
    id: int
    school_id: int
    device_id: int | None
    alert_type: str
    severity: str
    message: str
    acknowledged: bool
    created_at: datetime

    class Config:
        from_attributes = True


# -------------------------
# Ingest (normalized)
# -------------------------
class IngestDevice(BaseModel):
    asset_tag: str = ""
    serial_number: str = ""
    hostname: str = ""
    ip: str = ""


class IngestUser(BaseModel):
    email: str = ""


class IngestEvent(BaseModel):
    type: str = "web_access"
    url: str | None = None
    domain: str | None = None
    action: str | None = None  # blocked/allowed/observed
    category: str | None = None
    observed_at: str | None = None
    raw: str | None = None


class WebFilterIngest(BaseModel):
    api_key: str
    school_id: int
    source: str = "unknown"
    device: IngestDevice = IngestDevice()
    user: IngestUser = IngestUser()
    event: IngestEvent = IngestEvent()
