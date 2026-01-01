from sqlalchemy.orm import Session

from .models import Device
from .models_ext import PolicyRule
from .alerts import create_alert


def get_rules(db: Session, school_id: int) -> list[PolicyRule]:
    return (
        db.query(PolicyRule)
        .filter(PolicyRule.school_id == school_id, PolicyRule.enabled == True)  # noqa: E712
        .all()
    )


async def evaluate_event(
    db: Session,
    school_id: int,
    device: Device | None,
    event_type: str,
    payload: dict,
) -> None:
    """
    Evaluates normalized events against per-school PolicyRule records.

    Currently supported:
      - deny_domain: {"domain": "example.com"}
    """
    rules = get_rules(db, school_id)

    # Apply deny_domain rules to web/dns events
    if event_type in {"web_access", "dns_query"}:
        url = (payload.get("url") or "").lower()
        domain = (payload.get("domain") or "").lower()

        for r in rules:
            if r.rule_type != "deny_domain":
                continue

            bad_domain = (r.params or {}).get("domain", "")
            bad_domain = (bad_domain or "").lower().strip()
            if not bad_domain:
                continue

            haystack = domain or url
            if bad_domain in haystack:
                await create_alert(
                    db=db,
                    school_id=school_id,
                    device_id=device.id if device else None,
                    alert_type="security",
                    severity=r.severity,
                    message=(
                        f"Policy '{r.name}' triggered. "
                        f"Denied domain '{bad_domain}'. Observed: {domain or url}"
                    ),
                )
