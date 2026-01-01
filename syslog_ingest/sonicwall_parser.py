import re
from typing import Optional


# Regex patterns to extract common SonicWall web filter fields.
# SonicWall syslog formats vary by firmware; this parser is intentionally resilient.
DOMAIN_RE = re.compile(
    r"(?:dstname=|domain=|Host:)\s*(?P<domain>[A-Za-z0-9\.\-]+\.[A-Za-z]{2,})",
    re.IGNORECASE,
)
URL_RE = re.compile(
    r"(?:url=|URI=|Requested URL:)\s*(?P<url>https?://\S+)",
    re.IGNORECASE,
)
SRCIP_RE = re.compile(
    r"(?:src=|srcip=|Source IP:)\s*(?P<ip>\d{1,3}(?:\.\d{1,3}){3})",
    re.IGNORECASE,
)
USER_RE = re.compile(
    r"(?:user=|usr=|User:)\s*(?P<user>[A-Za-z0-9\.\-_@]+)",
    re.IGNORECASE,
)
ACTION_RE = re.compile(
    r"(?:action=|Result:|msg=)\s*(?P<action>allowed|blocked|deny|denied|drop|dropped)",
    re.IGNORECASE,
)
CATEGORY_RE = re.compile(
    r"(?:cat=|category=|Category:)\s*(?P<category>[A-Za-z0-9 _\-/]+)",
    re.IGNORECASE,
)


def parse_sonicwall_syslog(line: str) -> Optional[dict]:
    """
    Attempts to parse a SonicWall syslog line related to web filtering.

    Returns a normalized dict or None if the line is not relevant.

    Output example:
    {
      "type": "web_access",
      "url": "https://example.com",
      "domain": "example.com",
      "action": "blocked",
      "category": "Adult",
      "ip": "10.0.0.5",
      "user": "student@district.org",
      "raw": "<original syslog line>"
    }
    """
    if not line:
        return None

    raw = line.strip()
    lower = raw.lower()

    # Fast filter: ignore non-web related logs
    if not any(k in lower for k in ["url", "http", "https", "web", "category", "content filter", "cfs"]):
        return None

    url = None
    domain = None
    ip = None
    user = None
    action = None
    category = None

    m = URL_RE.search(raw)
    if m:
        url = m.group("url")

    m = DOMAIN_RE.search(raw)
    if m:
        domain = m.group("domain")

    m = SRCIP_RE.search(raw)
    if m:
        ip = m.group("ip")

    m = USER_RE.search(raw)
    if m:
        user = m.group("user")

    m = ACTION_RE.search(raw)
    if m:
        act = m.group("action").lower()
        if act in {"deny", "denied", "drop", "dropped"}:
            action = "blocked"
        else:
