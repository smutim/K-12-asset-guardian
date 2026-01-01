import os
from datetime import datetime
from sqlalchemy.orm import Session

from google.oauth2 import service_account
from googleapiclient.discovery import build

from ..models import Device
from ..models_ext import ExternalDeviceId, Event


GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/admin.directory.device.chromeos.readonly",
    "https://www.googleapis.com/auth/chrome.management.reports.readonly",
]


def _google_clients():
    """
    Uses a Service Account + Domain Wide Delegation (DWD).
    Required env vars:
      - GOOGLE_SA_JSON_PATH: path to service account json file
      - GOOGLE_DELEGATED_ADMIN: super admin email in the Google tenant
    """
    sa_path = os.getenv("GOOGLE_SA_JSON_PATH", "")
    delegated_user = os.getenv("GOOGLE_DELEGATED_ADMIN", "")

    if not sa_path or not delegated_user:
        raise RuntimeError("Missing GOOGLE_SA_JSON_PATH or GOOGLE_DELEGATED_ADMIN env vars")

    creds = service_account.Credentials.from_service_account_file(
        sa_path,
        scopes=GOOGLE_SCOPES,
    )
    creds = creds.with_subject(delegated_user)

    admin_svc = build("admin", "directory_v1", credentials=creds, cache_discovery=False)
    chrome_svc = build("chromemanagement", "v1", credentials=creds, cache_discovery=False)

    return admin_svc, chrome_svc


def _parse_rfc3339(dt_str: str | None) -> datetime | None:
    if not dt_str:
        return None
    # Common: 2026-01-01T12:34:56.789Z
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None


def sync_chromebooks_for_customer(
    db: Session,
    school_id: int,
    customer_id: str = "my_customer",
    page_size: int = 200,
) -> dict:
    """
    Pulls Chromebook inventory from Google Admin Directory API.
    Creates/updates Device rows and stores ExternalDeviceId(source='google') for google deviceId.
    """
    admin_svc, _ = _google_clients()

    page_token = None
    synced = 0

    while True:
        resp = admin_svc.chromeosdevices().list(
            customerId=customer_id,
            maxResults=page_size,
            pageToken=page_token,
            projection="FULL",
            orderBy="lastSync",
        ).execute()

        items = resp.get("chromeosdevices", []) or []
        for g in items:
            synced += 1

            serial = (g.get("serialNumber") or "").strip()
            if not serial:
                continue

            asset_tag = (g.get("annotatedAssetId") or "").strip() or serial
            model = (g.get("model") or "Chromebook").strip()
            os_ver = (g.get("osVersion") or "").strip()
            org_unit = (g.get("orgUnitPath") or "").strip()
            google_device_id = (g.get("deviceId") or "").strip()

            last_sync_raw = g.get("lastSync")
            last_seen = _parse_rfc3339(last_sync_raw)

            # Find or create device
            device = (
                db.query(Device)
                .filter(Device.school_id == school_id, Device.serial_number == serial)
                .first()
            )

            if not device:
                device = Device(
                    school_id=school_id,
                    asset_tag=asset_tag,
                    serial_number=serial,
                    device_type="Chromebook",
                    assigned_to="",
                    status="online" if last_seen else "unknown",
                    last_seen=last_seen,
                )
                db.add(device)
                db.flush()  # get device.id
            else:
                if asset_tag and device.asset_tag != asset_tag:
                    device.asset_tag = asset_tag
                if last_seen:
                    device.last_seen = last_seen
                    device.status = "online"

            # Store external mapping
            if google_device_id:
                existing = (
                    db.query(ExternalDeviceId)
                    .filter(
                        ExternalDeviceId.source == "google",
                        ExternalDeviceId.external_id == google_device_id,
                    )
                    .first()
                )
                if not existing:
                    db.add(
                        ExternalDeviceId(
                            device_id=device.id,
                            source="google",
                            external_id=google_device_id,
                        )
                    )

            # Store normalized event
            db.add(
                Event(
                    school_id=school_id,
                    device_id=device.id,
                    event_type="inventory_sync",
                    severity="info",
                    source="google",
                    message=f"Synced Chromebook {asset_tag}",
                    payload={
                        "serial": serial,
                        "asset_tag": asset_tag,
                        "model": model,
                        "os_version": os_ver,
                        "org_unit": org_unit,
                        "google_device_id": google_device_id,
                        "lastSync": last_sync_raw,
                    },
                )
            )

        db.commit()

        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    return {"synced": synced}
