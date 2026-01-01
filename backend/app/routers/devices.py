from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Device
from ..schemas import DeviceCreate, DeviceOut
from ..auth import get_current_user


router = APIRouter(prefix="/devices", tags=["devices"])


@router.post("", response_model=DeviceOut)
def create_device(
    payload: DeviceCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    # Enforce tenant isolation
    if payload.school_id != user.school_id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Forbidden")

    device = Device(
        school_id=payload.school_id,
        asset_tag=payload.asset_tag,
        serial_number=payload.serial_number,
        device_type=payload.device_type,
        assigned_to=payload.assigned_to,
        status="unknown",
    )

    db.add(device)
    db.commit()
    db.refresh(device)
    return device


@router.get("", response_model=list[DeviceOut])
def list_devices(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    # Users only see devices in their school
    return (
        db.query(Device)
        .filter(Device.school_id == user.school_id)
        .order_by(Device.asset_tag)
        .all()
    )


@router.get("/{device_id}", response_model=DeviceOut)
def get_device(
    device_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    device = db.get(Device, device_id)
    if not device or device.school_id != user.school_id:
        raise HTTPException(status_code=404, detail="Device not found")

    return device
