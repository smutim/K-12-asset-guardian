from __future__ import annotations

import json
import os
import socket
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from sonicwall_parser import parse_sonicwall_line


app = FastAPI(title="Syslog Ingest", version="0.1.0")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_json(obj: Any) -> Any:
    """
    Ensure payload is JSON-serializable.
    """
    try:
        json.dumps(obj)
        return obj
    except Exception:
        return {"_non_serializable": str(obj)}


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "ts": _utc_now_iso()}


@app.post("/ingest/sonicwall")
async def ingest_sonicwall(request: Request) -> JSONResponse:
    """
    Accept syslog content via HTTP POST.
    Body can be:
      - raw text (one or many lines)
      - JSON: {"message": "..."} or {"messages": ["...", "..."]}
    Returns normalized events.
    """
    content_type = request.headers.get("content-type", "")

    raw_lines: list[str] = []
    if "application/json" in content_type:
        body = await request.json()
        if isinstance(body, dict):
            if "messages" in body and isinstance(body["messages"], list):
                raw_lines = [str(x) for x in body["messages"]]
            elif "message" in body:
                raw_lines = [str(body["message"])]
            else:
                # If someone posts an arbitrary object, store it as a single line JSON
                raw_lines = [json.dumps(body)]
        elif isinstance(body, list):
            raw_lines = [json.dumps(x) if not isinstance(x, str) else x for x in body]
        else:
            raw_lines = [str(body)]
    else:
        # Treat as plain text
        text = (await request.body()).decode("utf-8", errors="replace")
        raw_lines = [ln for ln in text.splitlines() if ln.strip()]

    host = socket.gethostname()
    customer_id = request.headers.get("x-customer-id") or os.getenv("CUSTOMER_ID")

    events: list[Dict[str, Any]] = []
    for line in raw_lines:
        parsed = parse_sonicwall_line(line)
        event: Dict[str, Any] = {
            "source": "sonicwall",
            "received_at": _utc_now_iso(),
            "customer_id": customer_id,
            "ingest_host": host,
            "raw": line,
            "parsed": _safe_json(parsed),
        }
        events.append(event)

    return JSONResponse({"count": len(events), "events": events})

