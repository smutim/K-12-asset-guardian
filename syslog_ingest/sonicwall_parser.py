from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional


_SYSLOG_TS = re.compile(
    r"^(?P<ts>[A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+(?P<host>\S+)\s+(?P<rest>.*)$"
)

# Very lightweight key=value extractor for SonicWall-like logs
_KV = re.compile(r'(?P<k>[A-Za-z0-9_\-\.]+)=(?P<v>"[^"]*"|\S+)')


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _strip_quotes(v: str) -> str:
    if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
        return v[1:-1]
    return v


def parse_sonicwall_line(line: str) -> Dict[str, Any]:
    """
    Best-effort SonicWall syslog line parser.
    Returns a dictionary that is always safe to JSON serialize.
    """
    line = (line or "").strip()
    if not line:
        return {"ok": False, "error": "empty_line"}

    out: Dict[str, Any] = {
        "ok": True,
        "parsed_at": _utc_now_iso(),
    }

    m = _SYSLOG_TS.match(line)
    if m:
        out["syslog_ts_raw"] = m.group("ts")
        out["host"] = m.group("host")
        rest = m.group("rest")
    else:
        # Some SonicWall formats don't include the RFC-ish prefix
        rest = line

    # Extract key/value pairs if present
    kv: Dict[str, str] = {}
    for km in _KV.finditer(rest):
        k = km.group("k")
        v = _strip_quotes(km.group("v"))
        kv[k] = v

    if kv:
        out["fields"] = kv
        out["message"] = rest
    else:
        # No kv structure detected: keep raw message
        out["message"] = rest

    return out
