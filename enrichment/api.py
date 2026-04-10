"""
Enrichment API adapter.

To swap in a real provider, replace `_call_api` with a live implementation.
The rest of the pipeline consumes only the dict returned by `enrich_person`.

Expected return format:
{
    "employer": str | None,
    "job_title": str | None,
    "department": str | None,
    "confidence": float | None,   # 0.0 – 1.0
}
Returns None if no match was found.
"""

import random
import sys
import time
from pathlib import Path

# Allow imports to work both from the project root and as a bundled .exe
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config as _config

# --- Mock data used when no real API is configured ---

_MOCK_EMPLOYERS = [
    "Acme Corp", "Riverside Health", "Summit Financial", "Bluewave Tech",
    "City of Springfield", "Lakeside Unified School District", None,
]

_MOCK_TITLES = [
    "Software Engineer", "HR Manager", "Chief Executive Officer",
    "VP of People Operations", "Director of Talent Acquisition",
    "CFO", "Senior Vice President", "Marketing Coordinator",
    "Chief Human Resources Officer", "Managing Director", None,
]

_MOCK_DEPARTMENTS = [
    "Engineering", "Human Resources", "Finance", "People Operations",
    "Talent", "Executive", "Marketing", "Operations", None,
]


def _call_api(first_name: str, last_name: str, location: str, email: str = "") -> dict | None:
    """
    Calls the enrichment API if a key is configured, otherwise runs the mock.

    Email is sent as the primary match field; name and location are secondary.
    To swap in a real provider, replace the body of the `if api_key` block.
    The mock runs automatically when no key is saved.

    Example real implementation for PDL:
        import requests
        payload = {"first_name": first_name, "last_name": last_name, "location": location}
        if email:
            payload["work_email"] = email  # email is checked first by the API
        response = requests.post(
            "https://api.peopledatalabs.com/v5/person/enrich",
            headers={"X-Api-Key": api_key},
            json=payload,
        )
        if response.status_code == 200:
            data = response.json()
            return {
                "employer": data.get("job_company_name"),
                "job_title": data.get("job_title"),
                "department": data.get("job_company_industry"),
                "confidence": data.get("likelihood", 0) / 10,
            }
        return None
    """
    api_key = _config.get_api_key()

    if api_key:
        import requests
        payload = {
            "first_name": first_name,
            "last_name": last_name,
        }
        if email:
            payload["email"] = email
        if location:
            payload["location"] = location
        response = requests.post(
            "https://api.peopledatalabs.com/v5/person/enrich",
            headers={"X-Api-Key": api_key},
            json=payload,
        )
        if response.status_code == 200:
            resp = response.json()
            data = resp.get("data") or {}
            return {
                "employer":                   data.get("job_company_name"),
                "job_title":                  data.get("job_title"),
                "department":                 data.get("job_company_industry"),
                "confidence":                 resp.get("likelihood", 0) / 10,
                "birth_year":                 data.get("birth_year"),
                "linkedin_url":               data.get("linkedin_url"),
                "linkedin_username":          data.get("linkedin_username"),
                "facebook_url":               data.get("facebook_url"),
                "twitter_url":                data.get("twitter_url"),
                "work_email":                 data.get("work_email"),
                "recommended_personal_email": data.get("recommended_personal_email"),
                "mobile_phone":               data.get("mobile_phone"),
                "job_company_website":        data.get("job_company_website"),
                "job_company_size":           data.get("job_company_size"),
                "job_company_industry_v2":    data.get("job_company_industry_v2"),
                "job_start_date":             data.get("job_start_date"),
                "inferred_salary":            data.get("inferred_salary"),
            }
        return None

    # --- Mock (runs when no API key is configured) ---
    time.sleep(0.05)  # simulate network latency

    # ~20% chance of no match
    if random.random() < 0.2:
        return None

    return {
        "employer": random.choice(_MOCK_EMPLOYERS),
        "job_title": random.choice(_MOCK_TITLES),
        "department": random.choice(_MOCK_DEPARTMENTS),
        "confidence": round(random.uniform(0.5, 1.0), 2),
    }


def enrich_person(first_name: str, last_name: str, location: str, email: str = "") -> dict | None:
    """
    Enrich a single person. Email is used as the primary match field when provided.
    Retries once on exception. Returns enrichment dict or None if no match / repeated failure.
    """
    for attempt in range(2):
        try:
            return _call_api(first_name, last_name, location, email)
        except Exception as e:
            if attempt == 0:
                continue
            raise e
    return None
