_CSUITE_TERMS = {
    "ceo", "coo", "cfo", "cto", "chro", "cmo",
    "president", "evp", "svp", "managing director",
}

_HR_TERMS = {
    "human resources", "hr", "people operations",
    "talent", "chro", "chief people officer",
}

_LD_TERMS = {
    "learning and development", "l&d",
    "chief learning officer", "chief talent officer",
    "employee experience",
}

_MARKETING_DEPT_TERMS = {
    "marketing", "corporate responsibility", "corporate social responsibility",
    "csr", "community engagement", "community relations", "public affairs",
    "communications", "corporate communications", "government relations",
    "external affairs",
}

_MANAGER_LEVEL_TERMS = {
    "manager", "director", "vp", "vice president", "svp", "evp",
    "president", "chief", "cmo", "head of", "lead", "officer",
}


def _contains_any(text: str | None, terms: set[str]) -> bool:
    if not text:
        return False
    lower = text.lower()
    return any(term in lower for term in terms)


def is_csuite(job_title: str | None) -> bool:
    return _contains_any(job_title, _CSUITE_TERMS)


def is_hr(job_title: str | None, department: str | None) -> bool:
    return _contains_any(job_title, _HR_TERMS) or _contains_any(department, _HR_TERMS)


def is_ld(job_title: str | None, department: str | None) -> bool:
    return _contains_any(job_title, _LD_TERMS) or _contains_any(department, _LD_TERMS)


def is_marketing_comms(job_title: str | None, department: str | None, industry_v2: str | None = None) -> bool:
    """
    Flags people in Marketing, Corporate Responsibility, Community Engagement,
    or Public Affairs at Manager level or above.
    """
    in_dept = (
        _contains_any(department, _MARKETING_DEPT_TERMS)
        or _contains_any(industry_v2, _MARKETING_DEPT_TERMS)
    )
    title_in_area = _contains_any(job_title, _MARKETING_DEPT_TERMS)
    title_is_manager_plus = _contains_any(job_title, _MANAGER_LEVEL_TERMS)

    # Department is in scope AND title is manager+
    if in_dept and title_is_manager_plus:
        return True
    # Title itself names the area AND is manager+
    if title_in_area and title_is_manager_plus:
        return True
    return False
