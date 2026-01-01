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


@router.post("/goguardian")
async def ingest_goguardian(request: Request, db: Session = Depends(get_db)):
    """
    Adapter-friendly GoGuardian endpoint.

    Expected JSON:
    {
      "api_key":"...",
      "school_id":1,
      "device": {"serial_number":"", "asset_tag":"", "hostname":"", "ip":"", "mac":""},
      "user": {"email":"student@district.org"},
      "event": {"url":"...", "domain":"...", "action":"blocked|allowed", "category":"...", "rule":"...", "timestamp":"..."}
    }
    """
    body = await request.json()

    api_key = body.get("api_key", "")
    school_id = int(body.get("school_id") or 0)

    if not api_key or not school_id:
        raise HTTPException(status_code=400, detail="Missing api_key or school_id")

    if not validate_api_key(db, school_id, api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")

    dev = body.get("device") or {}
    usr = body.get("user") or {}
    ev = body.get("event") or {}

    serial = (dev.get("serial_number") or "").strip()
    asset = (dev.get("asset_tag") or "").strip()
    hostname = (dev.get("hostname") or "").strip()
    ip = (dev.get("ip") or "").strip()
    mac = (dev.get("mac") or "").strip()

    url = ev.get("url")
    domain = ev.get("domain")
    action = (ev.get("action") or "").lower().strip()
    category = ev.get("category")
    rule = ev.get("rule")
    timestamp = ev.get("timestamp")

    # Device correlation order: serial -> asset -> MAC -> IP
    device = None
    if serial:
        device = (
            db.query(Device)
            .filter(Device.school_id == school_id, Device.serial_number == serial)
            .first()
        )

    if not device and asset:
        device = (
            db.query(Device)
            .filter(Device.school_id == school_id, Device.asset_tag == asset)
            .first()
        )

    if not device and mac:
        dni = db.query(DeviceNetworkIdentity).filter(DeviceNetworkIdentity.mac == mac).first()
        if dni:
            device = db.get(Device, dni.device_id)

    if not device and ip:
        dni = db.query(DeviceNetworkIdentity).filter(DeviceNetworkIdentity.last_ip == ip).first()
        if dni:
            device = db.get(Device, dni.device_id)

    severity = "info" if action == "allowed" else "medium" if action == "blocked" else "info"

    payload = {
        "device": {"serial_number": serial, "asset_tag": asset, "hostname": hostname, "ip": ip, "mac": mac},
        "user": usr,
        "event": {
            "type": "web_access",
            "url": url,
            "domain": domain,
            "action": action,
            "category": category,
            "rule": rule,
            "timestamp": timestamp,
        },
        "source": "goguardian",
    }

    db.add(
        Event(
            school_id=school_id,
            device_id=device.id if device else None,
            event_type="web_access",
            severity=severity,
            source="goguardian",
            message=f"GoGuardian {action}: {domain or url or ''}",
            payload=payload,
        )
    )
    db.commit()

    if device:
        await evaluate_event(
            db=db,
            school_id=school_id,
            device=device,
            event_type="web_access",
            payload={
                "url": url,
                "domain": domain,
                "action": action,
                "category": category,
            },
        )

    return {"ok": True}
`
