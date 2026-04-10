"""
ACT Attendee Enrichment Tool

Usage:
    python main.py <input.xlsx> [output.xlsx]

If output filename is omitted, writes to <input_name>_enriched.xlsx in the same folder.
"""

import sys
import os
import logging
from pathlib import Path

from enrichment.reader import read_attendees
from enrichment.api import enrich_person
from enrichment.flags import is_csuite, is_hr, is_ld, is_marketing_comms
from enrichment.writer import write_results

logging.basicConfig(
    filename="enrichment.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)


def build_location(row: dict) -> str:
    """Combine whatever address fields exist into a single location string."""
    candidates = ["Address", "Street", "City", "State", "Zip", "ZIP", "Postal Code"]
    parts = [str(row[k]).strip() for k in candidates if k in row and row[k]]
    return ", ".join(parts)


def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <input.xlsx> [output.xlsx]")
        sys.exit(1)

    input_path = sys.argv[1]
    if not os.path.exists(input_path):
        print(f"File not found: {input_path}")
        sys.exit(1)

    input_stem = Path(input_path).stem
    input_dir = Path(input_path).parent
    output_path = sys.argv[2] if len(sys.argv) > 2 else str(input_dir / f"{input_stem}_enriched.xlsx")

    print(f"Reading {input_path}...")
    attendees = read_attendees(input_path)
    total = len(attendees)
    print(f"Found {total} attendee(s).\n")

    original_headers = list(attendees[0].keys()) if attendees else []

    matched = []
    unmatched = []
    flagged = 0

    for i, row in enumerate(attendees, start=1):
        first = str(row.get("First Name") or row.get("FirstName") or "").strip()
        last = str(row.get("Last Name") or row.get("LastName") or "").strip()
        email = str(row.get("Email") or row.get("Email Address") or row.get("E-mail") or "").strip()
        location = build_location(row)

        print(f"Processing {i} of {total}: {first} {last}...", end="\r")

        try:
            result = enrich_person(first, last, location, email)
        except Exception as e:
            logging.error(f"Row {i} ({first} {last}): API error — {e}")
            result = None

        if result is None:
            logging.info(f"Row {i} ({first} {last}): no match")
            unmatched.append(row)
            continue

        enriched_row = {
            **row,
            "employer":                   result.get("employer"),
            "job_title":                  result.get("job_title"),
            "department":                 result.get("department"),
            "job_company_industry_v2":    result.get("job_company_industry_v2"),
            "confidence":                 result.get("confidence"),
            "birth_year":                 result.get("birth_year"),
            "linkedin_url":               result.get("linkedin_url"),
            "linkedin_username":          result.get("linkedin_username"),
            "facebook_url":               result.get("facebook_url"),
            "twitter_url":                result.get("twitter_url"),
            "work_email":                 result.get("work_email"),
            "recommended_personal_email": result.get("recommended_personal_email"),
            "mobile_phone":               result.get("mobile_phone"),
            "job_company_website":        result.get("job_company_website"),
            "job_company_size":           result.get("job_company_size"),
            "job_start_date":             result.get("job_start_date"),
            "inferred_salary":            result.get("inferred_salary"),
            "hr_flag":       is_hr(result.get("job_title"), result.get("department")),
            "csuite_flag":   is_csuite(result.get("job_title")),
            "ld_flag":       is_ld(result.get("job_title"), result.get("department")),
            "marketing_flag": is_marketing_comms(
                result.get("job_title"),
                result.get("department"),
                result.get("job_company_industry_v2"),
            ),
        }

        if enriched_row["hr_flag"] or enriched_row["csuite_flag"] or enriched_row["ld_flag"] or enriched_row["marketing_flag"]:
            flagged += 1

        matched.append(enriched_row)

    print()  # newline after progress line
    print(f"\nWriting results to {output_path}...")
    write_results(output_path, original_headers, matched, unmatched)

    print("\n--- Summary ---")
    print(f"Total processed : {total}")
    print(f"Matched         : {len(matched)}")
    print(f"Unmatched       : {len(unmatched)}")
    print(f"Flagged (HR/C)  : {flagged}")
    print(f"Output          : {output_path}")
    print(f"Log             : enrichment.log")


if __name__ == "__main__":
    main()
