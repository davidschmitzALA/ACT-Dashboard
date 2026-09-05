"""
Parser for "FY27 WS Subs Final" PDF reports.

Expected tables:
  "Sub Sales Yesterday": Season | Subs Purchased | Total Ticket Paid Amount
  "Sub Sales to date":   Season | Production Season | Subs Purchased | Total Ticket Paid Amount

Returns dict with keys 'yesterday' and 'to_date'.
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


def parse_subs_pdf(filepath: str) -> dict:
    today = date.today().isoformat()
    results = {"yesterday": [], "to_date": []}

    settings = {"vertical_strategy": "lines", "horizontal_strategy": "lines"}

    with pdfplumber.open(filepath) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            tables = page.extract_tables(settings)

            for table in tables:
                if not table or len(table) < 2:
                    continue
                header = _trim_trailing_empty([str(c or "").strip() for c in table[0]])
                ncols = len(header)

                # Yesterday table: 3 columns — Season | Subs Purchased | Total Ticket Paid Amount
                if (
                    ncols == 3
                    and "Sub Sales Yesterday" in text
                    and not results["yesterday"]
                    and any("Season" in h for h in header)
                    and any("Subs" in h for h in header)
                ):
                    for row in table[1:]:
                        if not row or len(row) < 3:
                            continue
                        season = str(row[0] or "").strip()
                        subs = _to_int(row[1])
                        amount = _to_float(row[2])
                        if not season or "Grand Total" in season:
                            continue
                        results["yesterday"].append({
                            "date": today,
                            "show": season,
                            "subs_purchased": subs,
                            "revenue": amount,
                            "source": "yesterday",
                        })

                # To-date table: 4 columns — Season | Production Season | Subs Purchased | Total
                elif (
                    ncols == 4
                    and "Sub Sales to date" in text
                    and any("Season" in h for h in header)
                    and any("Subs" in h for h in header)
                ):
                    current_season = ""
                    for row in table[1:]:
                        if not row or len(row) < 4:
                            continue
                        season_cell = str(row[0] or "").strip()
                        production = str(row[1] or "").strip()
                        subs = _to_int(row[2])
                        amount = _to_float(row[3])
                        if season_cell:
                            current_season = season_cell
                        if "Grand Total" in (production or current_season):
                            continue
                        if not production or subs is None:
                            continue
                        results["to_date"].append({
                            "date": today,
                            "show": production,
                            "subs_purchased": subs,
                            "revenue": amount,
                            "source": "to_date",
                        })

    return results
