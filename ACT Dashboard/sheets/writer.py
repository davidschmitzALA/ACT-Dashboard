"""
Google Sheets writer for ACT Dashboard.

Authenticates using Application Default Credentials (ADC).
All writes use append-only pattern. Dashboard reads always use
the most recent date_ingested value per category.

Tab names match the spec exactly:
  daily_ticket_sales, subscriptions, sub_response_summary,
  performance_capacity, attendance, revenue_pacing,
  weekly_show_totals, conservatory, run_log
"""

import os
from datetime import datetime, timezone

import google.auth
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# Column headers for each tab — order matters for appending
HEADERS = {
    "daily_ticket_sales": [
        "date", "show", "revenue", "seats_sold", "source",
    ],
    "subscriptions": [
        "date", "show", "subs_purchased", "revenue", "source",
    ],
    "sub_response_summary": [
        "date_ingested", "category", "seat_qty", "amount", "renewal_pct", "base_hh",
    ],
    "performance_capacity": [
        "date_ingested", "show", "perf_date", "perf_time",
        "capacity", "pct_sold", "paid_count", "ticket_amount",
        "comps", "avg_ticket", "avail_seats",
    ],
    "attendance": [
        "date", "show", "venue", "curtain_time",
        "tickets_sold", "actual_attendance", "walk_outs", "late_seating",
        "concessions_sales", "merch_sales", "house_manager",
    ],
    "revenue_pacing": [
        "date_ingested", "category", "subcategory",
        "budget", "actual_to_date", "forecast", "remaining", "variance",
    ],
    "weekly_show_totals": [
        "date_ingested", "show", "subs_income", "single_income",
        "groups", "smats", "grand_total",
        "sub_tickets", "single_tickets", "total_tickets", "comp_tickets", "num_perfs",
    ],
    "conservatory": [
        "date_ingested", "program", "budget", "actual", "variance", "notes",
    ],
    "run_log": [
        "run_timestamp", "status", "files_processed", "errors",
    ],
}


class SheetsWriter:
    def __init__(self, sheet_id: str):
        self.sheet_id = sheet_id
        creds, _ = google.auth.default(scopes=SCOPES)
        self._service = build("sheets", "v4", credentials=creds)
        self._sheets_api = self._service.spreadsheets()
        self._ensure_tabs()

    # ------------------------------------------------------------------ #
    # Tab management                                                       #
    # ------------------------------------------------------------------ #

    def _ensure_tabs(self):
        """Create any missing tabs and write header rows."""
        meta = self._sheets_api.get(spreadsheetId=self.sheet_id).execute()
        existing = {s["properties"]["title"] for s in meta.get("sheets", [])}

        add_requests = []
        for tab in HEADERS:
            if tab not in existing:
                add_requests.append({
                    "addSheet": {"properties": {"title": tab}}
                })

        if add_requests:
            self._sheets_api.batchUpdate(
                spreadsheetId=self.sheet_id,
                body={"requests": add_requests},
            ).execute()

        for tab, cols in HEADERS.items():
            if tab not in existing:
                self._write_header(tab, cols)

    def _write_header(self, tab: str, cols: list[str]):
        self._sheets_api.values().update(
            spreadsheetId=self.sheet_id,
            range=f"{tab}!A1",
            valueInputOption="RAW",
            body={"values": [cols]},
        ).execute()

    # ------------------------------------------------------------------ #
    # Generic append                                                       #
    # ------------------------------------------------------------------ #

    def _append(self, tab: str, rows: list[dict]):
        if not rows:
            return
        cols = HEADERS[tab]
        values = [[str(row.get(c, "") or "") for c in cols] for row in rows]
        self._sheets_api.values().append(
            spreadsheetId=self.sheet_id,
            range=f"{tab}!A1",
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": values},
        ).execute()

    # ------------------------------------------------------------------ #
    # Public write methods                                                 #
    # ------------------------------------------------------------------ #

    def write_daily_ticket_sales(self, rows: list[dict]):
        self._append("daily_ticket_sales", rows)

    def write_subscriptions(self, rows: list[dict]):
        self._append("subscriptions", rows)

    def write_sub_response_summary(self, rows: list[dict]):
        self._append("sub_response_summary", rows)

    def write_performance_capacity(self, rows: list[dict]):
        self._append("performance_capacity", rows)

    def write_attendance(self, rows: list[dict]):
        self._append("attendance", rows)

    def write_revenue_pacing(self, rows: list[dict]):
        self._append("revenue_pacing", rows)

    def write_weekly_show_totals(self, rows: list[dict]):
        self._append("weekly_show_totals", rows)

    def write_conservatory(self, rows: list[dict]):
        self._append("conservatory", rows)

    # ------------------------------------------------------------------ #
    # Run log                                                              #
    # ------------------------------------------------------------------ #

    def log_run(self, status: str, files: list[str], errors: list[str]):
        ts = datetime.now(timezone.utc).isoformat()
        self._append("run_log", [{
            "run_timestamp": ts,
            "status": status,
            "files_processed": "; ".join(files),
            "errors": "; ".join(errors),
        }])

    def get_last_run_timestamp(self) -> str | None:
        """Return the ISO timestamp of the last *successful* run, or None."""
        try:
            resp = self._sheets_api.values().get(
                spreadsheetId=self.sheet_id,
                range="run_log!A:B",
            ).execute()
        except HttpError:
            return None

        values = resp.get("values", [])
        # Walk backwards to find last successful run
        for row in reversed(values[1:]):  # skip header
            if len(row) >= 2 and row[1].lower() in ("success", "partial", "warning"):
                return row[0]

        return None
