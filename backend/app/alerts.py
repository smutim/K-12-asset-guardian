from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from .models import Alert, Device, User
from .emailer import send_email


# Defaults (you will move these into PolicyRule records per school)
DEFAULT_OFFLINE_THRESHOLD_MINUTES = 20
DEFAULT_LOW_BATTERY_THRESHOLD = 15


def get_admin_emails(db: Session, school_id: int) -> list[str]:
    admins = (
        db.query(User)
        .filter(User.school_id == school_id, User.is_admin == True)  # noqa: E712
        .all()
    )
    return [a.email for a in admins]


async def create_alert(
    db: Session,
    school_id: int,
    device_id: int | None,
    alert_type: str,
    severity: str,
    message: str,
) -> Alert:
    alert = Alert(
        school_id=school_id,
        device_id=device_id,
        alert_type=alert_type,
        severity=severity,
        message=message,
        created_at=datetime.utcnow(),
        acknowledged=False,
    )

    db.add(alert)
    db.commit()
    db.refresh(alert)

    # Notify admins (simple MVP)
    subject = f"[{severity.upper()}] K12 Asset Guardian alert: {alert_type}"
    for email in get_admin_emails(db, school_id):
        await send_email(email, subject, message)

    return alert


async def evaluate_device_thresholds(db: Session, device: Device) -> None:
    """
    Runs basic device threshold checks (battery, etc.) on heartbeat/sync updates.
    """
    if (
        device.battery_percent is not None
        and device.battery_percent <= DEFAULT_LOW_BATTERY_THRESHOLD
    ):
        await create_alert(
            db=db,
            school_id=device.school_id,
            device_id=device.id,
            alert_type="threshold",
            severity="medium",
            message=f"Device {device.asset_tag} battery is low ({device.battery_percent}%).",
        )


def offline_sweep(db: Session, school_id: int | None = None) -> int:
    """
    Marks devices offline if last_seen is older than the threshold.
    Returns number of devices updated.
    """
    cutoff = datetime.utcnow() - timedelta(minutes=DEFAULT_OFFLINE_THRESHOLD_MINUTES)

    q = db.query(Device).filter(Device.last_seen != None)  # noqa: E711
    if school_id is not None:
        q = q.filter(Device.school_id == school_id)

    devices = q.all()
    changed = 0

    for d in devices:
        if d.last_seen and d.last_seen < cutoff and d.status != "offline":
            d.status = "offline"
            changed += 1

    if changed:
        db.commit()

    return changed
