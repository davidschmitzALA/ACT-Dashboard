"""
Parser for House Manager Report (HMR) plain-text emails.

Extracts labeled fields by exact label matching.
Returns a single dict, or None if the body doesn't look like an HMR.
"""

import re
from datetime import date, datetime


def _field(text: str, label: str) -> str:
    """Extract the value immediately after a bold label."""
    # Labels in the plain-text body appear as "LABEL:\nValue" or "LABEL:\r\nValue"
    pattern = re.compile(
        rf"(?:^|\n){re.escape(label)}[:\s]*\r?\n([^\n]+)",
        re.IGNORECASE | re.MULTILINE,
    )
    m = pattern.search(text)
    return m.group(1).strip() if m else ""


def _clean_currency(val: str) -> float | None:
    s = re.sub(r"[$,\s]", "", val)
    try:
        return float(s)
    except ValueError:
        return None


def _clean_int(val: str) -> int | None:
    s = re.sub(r"[,\s]", "", val)
    try:
        return int(float(s))
    except ValueError:
        return None


def _normalize_date(date_str: str) -> str:
    """Try common date formats and return ISO YYYY-MM-DD; fall back to original string."""
    formats = [
        "%B %d, %Y",   # May 18, 2026
        "%B %d %Y",    # May 18 2026
        "%b %d, %Y",   # May 18, 2026 (abbreviated month)
        "%b %d %Y",    # May 18 2026
        "%m/%d/%Y",    # 05/18/2026
        "%m/%d/%y",    # 05/18/26
        "%Y-%m-%d",    # already ISO
    ]
    s = date_str.strip()
    for fmt in formats:
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    return s  # return as-is if nothing matched


def parse_hmr_email(body_text: str) -> dict | None:
    if not body_text or "HOUSE MANAGER" not in body_text.upper():
        return None

    house_manager = _field(body_text, "HOUSE MANAGER")
    show = _field(body_text, "SHOW/EVENT TITLE")
    venue = _field(body_text, "Venue")
    date_raw = _field(body_text, "DATE")
    curtain_time = _field(body_text, "CURTAIN TIME")
    sold_actual = _field(body_text, "SOLD/ACTUAL")
    walk_outs = _field(body_text, "WALK OUTS")
    late_seating = _field(body_text, "LATE SEATING")
    concessions = _field(body_text, "CONCESSIONS SALES")
    merch = _field(body_text, "MERCH SALES")

    # Parse SOLD/ACTUAL: "134/107"
    tickets_sold = None
    actual_attendance = None
    if "/" in sold_actual:
        parts = sold_actual.split("/", 1)
        tickets_sold = _clean_int(parts[0])
        actual_attendance = _clean_int(parts[1])

    # Normalize date to ISO format (YYYY-MM-DD) for consistent sorting
    perf_date = _normalize_date(date_raw) if date_raw else date.today().isoformat()

    return {
        "date": perf_date,
        "show": show,
        "venue": venue,
        "curtain_time": curtain_time,
        "tickets_sold": tickets_sold,
        "actual_attendance": actual_attendance,
        "walk_outs": _clean_int(walk_outs),
        "late_seating": _clean_int(late_seating),
        "concessions_sales": _clean_currency(concessions),
        "merch_sales": _clean_currency(merch),
        "house_manager": house_manager,
    }
