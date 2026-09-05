"""
ACT Dashboard — Cloud Run entrypoint.

Runs at 10:30am Pacific via Cloud Scheduler, and on-demand via GET/POST /refresh.
Reads Gmail inbox, parses attachments, writes to Google Sheets.
"""

import os
import tempfile
import traceback
from datetime import datetime, timezone

from flask import Flask, jsonify, request

from ingestion.gmail_reader import GmailReader
from sheets.writer import SheetsWriter

app = Flask(__name__)


@app.after_request
def add_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


@app.route("/refresh", methods=["OPTIONS"])
def refresh_preflight():
    return "", 204

SHEET_ID = os.environ.get("SHEET_ID", "1O4P6gVsYg9eMU2a4d8h7RzVVjIWGFqDh90dyyhAxK0A")


def _note(files_processed, warnings, label, subject, count):
    """Record a processed file, flagging it when the parse produced no rows.

    A parser that silently returns nothing used to be logged as a plain
    success, which hid broken report formats for months.
    """
    files_processed.append(f"{label} ({subject[:40]}) [{count} rows]")
    if count == 0:
        warnings.append(f"{label} ({subject[:40]}) produced 0 rows")


def run_ingestion():
    writer = SheetsWriter(SHEET_ID)
    gmail = GmailReader()

    files_processed = []
    warnings = []
    errors = []

    last_run = writer.get_last_run_timestamp()
    messages = gmail.fetch_unread_since(last_run)

    for msg in messages:
        subject = msg.get("subject", "")
        subject_lower = subject.lower()
        try:
            if "mainstage yesterday" in subject_lower:
                from parsers.mainstage_pdf import parse_mainstage_pdf
                rows = []
                attachment = gmail.get_first_attachment(msg["id"])
                if attachment:
                    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                        f.write(attachment)
                        fname = f.name
                    data = parse_mainstage_pdf(fname)
                    os.unlink(fname)
                    rows = data["yesterday"] + data["to_date"]
                    writer.write_daily_ticket_sales(rows)
                _note(files_processed, warnings, "Mainstage Yesterday PDF", subject, len(rows))

            elif "ws subs" in subject_lower:
                from parsers.subs_pdf import parse_subs_pdf
                rows = []
                attachment = gmail.get_first_attachment(msg["id"])
                if attachment:
                    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                        f.write(attachment)
                        fname = f.name
                    data = parse_subs_pdf(fname)
                    os.unlink(fname)
                    rows = data["yesterday"] + data["to_date"]
                    writer.write_subscriptions(rows)
                _note(files_processed, warnings, "WS Subs PDF", subject, len(rows))

            elif "unsold" in subject_lower or "potential" in subject_lower:
                from parsers.capacity_pdf import parse_capacity_pdf
                rows = []
                attachment = gmail.get_first_attachment(msg["id"])
                if attachment:
                    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                        f.write(attachment)
                        fname = f.name
                    rows = parse_capacity_pdf(fname)
                    os.unlink(fname)
                    writer.write_performance_capacity(rows)
                _note(files_processed, warnings, "Capacity PDF", subject, len(rows))

            elif "hmr" in subject_lower:
                from parsers.hmr_email import parse_hmr_email
                body = msg.get("body_text", "")
                data = parse_hmr_email(body)
                rows = [data] if data else []
                if rows:
                    writer.write_attendance(rows)
                _note(files_processed, warnings, "HMR email", subject, len(rows))

            elif "revenue pacing" in subject_lower:
                from parsers.revenue_excel import parse_revenue_excel
                count = 0
                attachment = gmail.get_first_attachment(msg["id"])
                if attachment:
                    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
                        f.write(attachment)
                        fname = f.name
                    data = parse_revenue_excel(fname)
                    os.unlink(fname)
                    other = data.get("other_income", [])
                    writer.write_revenue_pacing(data["pacing"])
                    writer.write_conservatory(data["conservatory"])
                    writer.write_weekly_show_totals(other)
                    count = len(data["pacing"]) + len(data["conservatory"]) + len(other)
                _note(files_processed, warnings, "Revenue Pacing Excel", subject, count)

            elif "weekly sales" in subject_lower:
                from parsers.weekly_excel import parse_weekly_excel
                count = 0
                attachment = gmail.get_first_attachment(msg["id"])
                if attachment:
                    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
                        f.write(attachment)
                        fname = f.name
                    data = parse_weekly_excel(fname)
                    os.unlink(fname)
                    writer.write_weekly_show_totals(data["shows"])
                    writer.write_conservatory(data["conservatory"])
                    count = len(data["shows"]) + len(data["conservatory"])
                _note(files_processed, warnings, "Weekly Sales Excel", subject, count)

            elif "subscription response" in subject_lower:
                from parsers.sub_response_excel import parse_sub_response_excel
                rows = []
                attachment = gmail.get_first_attachment(msg["id"])
                if attachment:
                    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
                        f.write(attachment)
                        fname = f.name
                    rows = parse_sub_response_excel(fname)
                    os.unlink(fname)
                    writer.write_sub_response_summary(rows)
                _note(files_processed, warnings, "Sub Response Excel", subject, len(rows))

            else:
                # Unrecognized subject — skip silently
                continue

            gmail.mark_as_read(msg["id"])

        except Exception as exc:
            err = f"{subject[:50]}: {exc}"
            errors.append(err)
            traceback.print_exc()

    if errors:
        status = "partial" if files_processed else "error"
    elif warnings:
        status = "warning"
    else:
        status = "success"

    writer.log_run(status, files_processed, errors + warnings)

    return {
        "status": status,
        "files_processed": len(files_processed),
        "files": files_processed,
        "warnings": warnings,
        "errors": errors,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.route("/refresh", methods=["GET", "POST"])
def refresh():
    result = run_ingestion()
    return jsonify(result)


@app.route("/debug/gmail", methods=["GET"])
def debug_gmail():
    """Return the list of unread messages without processing them."""
    try:
        from ingestion.gmail_reader import GmailReader
        gmail = GmailReader()
        messages = gmail.fetch_unread_since(None)
        return jsonify({
            "count": len(messages),
            "messages": [
                {"id": m["id"], "subject": m.get("subject", ""), "has_attachments": m.get("has_attachments")}
                for m in messages
            ]
        })
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


@app.route("/debug/attachment/<msg_id>", methods=["GET"])
def debug_attachment(msg_id):
    """Show details about the first attachment of a message."""
    try:
        import base64
        from ingestion.gmail_reader import GmailReader
        gmail = GmailReader()
        svc = gmail._service

        msg = svc.users().messages().get(userId="me", id=msg_id, format="full").execute()

        def find_parts(payload, depth=0):
            parts_info = []
            mime = payload.get("mimeType", "")
            filename = payload.get("filename", "")
            body = payload.get("body", {})
            size = body.get("size", 0)
            attachment_id = body.get("attachmentId", "")
            parts_info.append({
                "depth": depth,
                "mimeType": mime,
                "filename": filename,
                "size": size,
                "hasAttachmentId": bool(attachment_id),
            })
            for part in payload.get("parts", []):
                parts_info.extend(find_parts(part, depth + 1))
            return parts_info

        parts = find_parts(msg["payload"])

        # Try downloading first real attachment and show first 100 bytes
        data = gmail.get_first_attachment(msg_id)
        preview = None
        if data:
            preview = base64.b64encode(data[:100]).decode()

        return jsonify({"parts": parts, "attachment_preview_b64": preview, "attachment_size": len(data) if data else 0})
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "service": "ACT Dashboard Ingestion",
        "endpoints": ["/refresh", "/health"],
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
