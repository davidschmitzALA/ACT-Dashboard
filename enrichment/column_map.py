"""
Auto-detects which columns in a spreadsheet correspond to the fields
the enrichment pipeline needs. Returns best guesses; user can override.
"""

# Each entry: (field_key, display_label, required, hint)
FIELDS = [
    ("first_name", "First Name",    True,  "e.g. First Name, fname, Patron First"),
    ("last_name",  "Last Name",     True,  "e.g. Last Name, lname, Patron Last"),
    ("email",      "Email Address", False, "e.g. Email, Email Address, E-mail"),
    ("address",    "Street Address", False, "e.g. Address, Street, Addr"),
    ("city",       "City",          False, "e.g. City, Town"),
    ("state",      "State",         False, "e.g. State, ST, Province"),
    ("zip",        "Zip / Postal",  False, "e.g. Zip, ZIP, Postal Code"),
]

# Keywords to look for when guessing each field
_HINTS: dict[str, list[str]] = {
    "first_name": ["first name", "firstname", "fname", "first", "given name", "givenname"],
    "last_name":  ["last name", "lastname", "lname", "last", "surname", "family name"],
    "email":      ["email", "email address", "e-mail", "emailaddress", "e mail"],
    "address":    ["address", "street", "addr", "street address"],
    "city":       ["city", "town", "municipality"],
    "state":      ["state", "province", "region"],
    "zip":        ["zip", "postal", "postcode", "zip code", "zipcode"],
}


def detect(headers: list[str]) -> dict[str, str | None]:
    """
    Given a list of column headers, return a best-guess mapping
    of field_key -> header string (or None if no match found).
    """
    lower_headers = [h.lower() for h in headers]
    mapping: dict[str, str | None] = {}

    for field_key, _, _, _ in FIELDS:
        hints = _HINTS[field_key]
        matched = None

        # Exact match first
        for hint in hints:
            for i, lh in enumerate(lower_headers):
                if lh == hint:
                    matched = headers[i]
                    break
            if matched:
                break

        # Partial match fallback
        if not matched:
            for hint in hints:
                for i, lh in enumerate(lower_headers):
                    if hint in lh or lh in hint:
                        matched = headers[i]
                        break
                if matched:
                    break

        mapping[field_key] = matched

    return mapping


def extract_name_and_location(row: dict, mapping: dict[str, str | None]) -> tuple[str, str, str, str]:
    """
    Given a row and an active mapping, return (first_name, last_name, location_string, email).
    """
    def get(key):
        col = mapping.get(key)
        if col and col in row and row[col]:
            return str(row[col]).strip()
        return ""

    first = get("first_name")
    last = get("last_name")
    email = get("email")

    parts = [get(k) for k in ("address", "city", "state", "zip")]
    location = ", ".join(p for p in parts if p)

    return first, last, location, email
