"""
Parser for "FY26 Mainstage Yesterday and To Date" PDF reports.

Expected tables:
  Page 2 — "Mainstage Single Sales Yesterday": Production Season | Ticket Paid Amount | Seats Sold
  Page 3 — "Mainstage Single Sales to Date":   Production Season | Ticket Paid Amt    | Seats Sold

Returns dict with keys 'yesterday' and 'to_date', each a list of row dicts.
"""

import re
from datetime import date

import pdfplumber


def _to_float(val) -> float | None:
    if val is None:
        return None
    s = re.sub(r"[$,\s]", "", str(val))
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


def _trim_trailing_empty(cells: list) -> list:
    """Drop trailing blank cells.

    FY27 Tessitura exports append an empty column to each table, which broke
    the exact column-count checks below.
    """
    out = list(cells)
    while out and not str(out[-1] or "").strip():
        out.pop()
    return out


def _extract_summary_table(page) -> list[dict] | None:
    """
    Extract the 3-column summary table (Production Season, Amount, Seats).
    Returns None if no matching table found on this page.
    """
    settings = {"vertical_strategy": "lines", "horizontal_strategy": "lines"}
    tables = page.extract_tables(settings)

    for table in tables:
        if not table or len(table) < 2:
            continue
        header = _trim_trailing_empty([str(c or "").strip() for c in table[0]])
        # Match: 3 columns, first contains "Production", second contains "Ticket"
        if len(header) != 3:
            continue
        if not any("Production" in h for h in header):
            continue
        if not any("Ticket" in h for h in header):
            continue

        rows = []
        for row in table[1:]:
            if not row or len(row) < 3:
                continue
            show = str(row[0] or "").strip()
            amount = _to_float(row[1])
            seats = _to_int(row[2])
            if not show or "Grand Total" in show or "Total" in show:
                continue
            if amount is None:
                continue
            rows.append({"show": show, "revenue": amount, "seats_sold": seats})
        if rows:
            return rows

    return None


def parse_mainstage_pdf(filepath: str) -> dict:
    today = date.today().isoformat()
    results = {"yesterday": [], "to_date": []}

    with pdfplumber.open(filepath) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""

            is_yesterday_page = (
                "Mainstage Single Sales Yesterday" in text
                and "to Date" not in text.split("Mainstage Single Sales Yesterday")[0]
            )
            is_to_date_page = "Mainstage Single Sales to Date" in text and "Price Type" not in text

            rows = _extract_summary_table(page)
            if rows is None:
                continue

            if is_yesterday_page and not results["yesterday"]:
                for r in rows:
                    r.update({"date": today, "source": "yesterday"})
                results["yesterday"] = rows

            elif is_to_date_page and not results["to_date"]:
                for r in rows:
                    r.update({"date": today, "source": "to_date"})
                results["to_date"] = rows

    return results
