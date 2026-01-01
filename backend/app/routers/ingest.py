from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Device
from ..models_ext import Event, SchoolApiKey, DeviceNetworkIdentity
from ..policy_engine import evaluate_event


router = APIRouter(prefix="/ingest", tags=["ingest"])


def validate_api_key(db: Session, school_id: int, api_key: str) -> bool:
    rec = (
        db.query(SchoolApiKey)
        .filter(
            SchoolApiKey.school_id == school_id,
            SchoolApiKey.key == api_key,
            SchoolApiKey.enabled == True,  # noqa: E712
        )
        .first()
    )
    return rec is not None


@router.post("/webfilter")
async def ingest_webfilter(request: Request, db: Session = Depends(get_db)):
    """
    Generic normalized ingest endpoint for firewall/web filter events.

    Expected JSON:
    {
      "api_key": "...",
      "school_id": 1,
      "source": "sonicwall|goguardian|lightspeed|securly|umbrella|other",
      "device": {"asset_tag":"", "serial_number":"", "hostname":"", "ip":""},
      "user": {"email":""},
      "event": {"type":"web_access", "url":"...", "domain":"...", "action":"blocked|allowed|observed", "category":"..."}
    }
    """
    body = await request.json()

    api_key = body.get("api_key", "")
    school_id = int(body.get("school_id") or 0)
    source = body.get("source", "unknown")

    if not api_key or not school_id:
        raise HTTPException(status_code=400, detail="Missing api_key or school_id")

    if not validate_api_key(db, school_id, api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")

    dev = body.get("device") or {}
    usr = body.get("user") or {}
    ev = body.get("event") or {}

    asset_tag = (dev.get("asset_tag") or "").strip()
    serial = (dev.get("serial_number") or "").strip()
    hostname = (dev.get("hostname") or "").strip()
    ip = (dev.get("ip") or "").strip()

    event_type = (ev.get("type") or "web_access").strip()
    url = ev.get("url")
    domain = ev.get("domain")
    action = (ev.get("action") or "").lower().strip()
    category = ev.get("category")

    # Device correlation order: serial -> asset tag -> IP (best effort)
    device = None
    if serial:
        device = (
            db.query(Device)
            .filter(Device.school_id == school_id, Device.serial_number == serial)
            .first()
        )

    if not device and asset_tag:
        device = (
            db.query(Device)
            .filter(Device.school_id == school_id, Device.asset_tag == asset_tag)
            .first()
        )

    if not device and ip:
        dni = db.query(DeviceNetworkIdentity).filter(DeviceNetworkIdentity.last_ip == ip).first()
        if dni:
            device = db.get(Device, dni.device_id)

    # Normalize severity for event table
    severity = "info"
    if action == "blocked":
        severity = "medium"

    payload = {
        "device": {"asset_tag": asset_tag, "serial_number": serial, "hostname": hostname, "ip": ip},
        "user": usr,
        "event": {
            "type": event_type,
            "url": url,
            "domain": domain,
            "action": action,
            "category": category,
        },
        "source": source,
    }

    db.add(
        Event(
            school_id=school_id,
            device_id=device.id if device else None,
            event_type=event_type,
            severity=severity,
            source=source,
            message=f"{event_type} {action}: {domain or url or ''}",
            payload=payload,
        )
    )
    db.commit()

    # Policy evaluation (deny domains, etc.)
    if device:
        await evaluate_event(
            db=db,
            school_id=school_id,
            device=device,
            event_type=event_type,
            payload={
                "url": url,
                "domain": domain,
                "action": action,
                "category": category,
            },
        )

    return {"ok": True}
