"""
Parser for "Unsold / Potential [Show] by performance week" PDF reports.

Columns: ProdID | Weeks in Date | Days in Date | Perf Time | Capacity |
         % Sold | Paid Count | TIcket Reserved Amount | Comps |
         Avg Sub & Single | Avail Seats to Sell

Show name is extracted from the PDF title text.
Uses multi-strategy table extraction to handle both bordered and borderless pages.
"""

import re
from datetime import date

import pdfplumber


def _to_float(val) -> float | None:
    if val is None:
        return None
    s = re.sub(r"[$,%\s]", "", str(val))
    try:
        return float(s)
    except ValueError:
        return None


def _to_int(val) -> int | None:
    if val is None:
        return None
    s = re.sub(r"[,\s]", "", str(val))
    try:
        return int(float(s))
    except ValueError:
        return None


def _extract_show_name(text: str) -> str:
    """Extract show name from title line like 'Unsold / Potential Hamnet by performance week'."""
    m = re.search(
        r"Unsold\s*/\s*Potential\s+(.+?)\s+by\s+performance\s+week",
        text,
        re.IGNORECASE,
    )
    if m:
        return m.group(1).strip()
    return "Unknown Show"


def _extract_data_rows(page) -> list[list[str]]:
    """
    Try multiple pdfplumber strategies to extract rows containing performance dates.
    Returns a flat list of raw string rows (each row is a list of cell strings).
    """
    strategies = [
        {"vertical_strategy": "lines", "horizontal_strategy": "lines"},
        {"vertical_strategy": "text", "horizontal_strategy": "text"},
        {"vertical_strategy": "lines", "horizontal_strategy": "text"},
        {"vertical_strategy": "text", "horizontal_strategy": "lines"},
    ]

    best_rows = []

    for settings in strategies:
        tables = page.extract_tables(settings)
        candidate_rows = []
        for table in (tables or []):
            for row in (table or []):
                if not row:
                    continue
                raw = [str(c or "").strip() for c in row]
                if len(raw) < 8:
                    continue
                # A valid data row has a date in position 2 (M/D/YY)
                perf_date = raw[2] if len(raw) > 2 else ""
                if re.match(r"\d+/\d+/\d+", perf_date):
                    candidate_rows.append(raw)

        if len(candidate_rows) > len(best_rows):
            best_rows = candidate_rows

    return best_rows


def parse_capacity_pdf(filepath: str) -> list[dict]:
    today = date.today().isoformat()
    rows = []
    show_name = "Unknown Show"

    with pdfplumber.open(filepath) as pdf:
        for page_num, page in enumerate(pdf.pages):
            text = page.extract_text() or ""

            if page_num == 0:
                show_name = _extract_show_name(text)

            data_rows = _extract_data_rows(page)

            for raw in data_rows:
                perf_date = raw[2] if len(raw) > 2 else ""
                perf_time = raw[3] if len(raw) > 3 else ""

                # Skip week-total rows
                if not perf_date or "Total" in perf_date or "Grand" in perf_date:
                    continue

                # Validate date format M/D/YY
                if not re.match(r"\d+/\d+/\d+", perf_date):
                    continue

                capacity = _to_int(raw[4]) if len(raw) > 4 else None
                pct_sold = _to_float(raw[5]) if len(raw) > 5 else None
                paid_count = _to_int(raw[6]) if len(raw) > 6 else None
                ticket_amount = _to_float(raw[7]) if len(raw) > 7 else None
                comps = _to_int(raw[8]) if len(raw) > 8 else None
                avg_ticket = _to_float(raw[9]) if len(raw) > 9 else None
                avail_seats = _to_int(raw[10]) if len(raw) > 10 else None

                rows.append({
                    "date_ingested": today,
                    "show": show_name,
                    "perf_date": perf_date,
                    "perf_time": perf_time,
                    "capacity": capacity,
                    "pct_sold": pct_sold,
                    "paid_count": paid_count,
                    "ticket_amount": ticket_amount,
                    "comps": comps,
                    "avg_ticket": avg_ticket,
                    "avail_seats": avail_seats,
                })

    return rows
