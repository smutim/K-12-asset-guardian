import os
import socket
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

from sonicwall_parser import parse_sonicwall_syslog


load_dotenv()

# -------------------------
# Configuration (env vars)
# -------------------------
SYSLOG_HOST = os.getenv("SYSLOG_HOST", "0.0.0.0")
SYSLOG_PORT = int(os.getenv("SYSLOG_PORT", "1514"))  # non-privileged UDP port

API_BASE = os.getenv("API_BASE", "http://backend:8000")
INGEST_ENDPOINT = f"{API_BASE}/ingest/webfilter"

SCHOOL_ID = int(os.getenv("SCHOOL_ID", "1"))
SCHOOL_API_KEY = os.getenv("SCHOOL_API_KEY", "")
SOURCE_NAME = os.getenv("SOURCE_NAME", "sonicwall")

SOCKET_BUFFER = 8192


def send_to_backend(payload: dict) -> None:
    try:
        r = requests.post(INGEST_ENDPOINT, json=payload, timeout=10)
        if r.status_code >= 300:
            print(
                "[syslog_ingest] Backend rejected event:",
                r.status_code,
                r.text[:300],
            )
    except Exception as exc:
        print("[syslog_ingest] Failed to send event:", exc)


def run_udp_server():
    if not SCHOOL_API_KEY:
        raise RuntimeError("Missing SCHOOL_API_KEY environment variable")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((SYSLOG_HOST, SYSLOG_PORT))

    print(
        f"[syslog_ingest] Listening on UDP {SYSLOG_HOST}:{SYSLOG_PORT} "
        f"→ {INGEST_ENDPOINT}"
    )

    while True:
        data, addr = sock.recvfrom(SOCKET_BUFFER)
        line = data.decode("utf-8", errors="ignore")

        parsed = parse_sonicwall_syslog(line)
        if not parsed:
            continue

        payload = {
            "api_key": SCHOOL_API_KEY,
            "school_id": SCHOOL_ID,
            "source": SOURCE_NAME,
            "device": {
                # SonicWall often only knows the source IP
                "asset_tag": "",
                "serial_number": "",
                "hostname": "",
                "ip": parsed.get("ip") or "",
            },
            "user": {
                "email":
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"status": "ok", "service": "k-12-asset-guardian"}
