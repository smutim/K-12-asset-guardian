from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Alert
from ..schemas import AlertOut
from ..auth import get_current_user


router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertOut])
def list_alerts(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    return (
        db.query(Alert)
        .filter(Alert.school_id == user.school_id)
        .order_by(Alert.created_at.desc())
        .all()
    )


@router.post("/{alert_id}/ack", response_model=AlertOut)
def acknowledge_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    alert = db.get(Alert, alert_id)
    if not alert or alert.school_id != user.school_id:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.acknowledged = True
    db.commit()
    db.refresh(alert)
    return alert
