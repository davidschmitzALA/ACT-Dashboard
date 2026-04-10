"""
Strategic Counsel engagement template.

Each Strategic Counsel engagement is unique, so this provides a clean
framework of standard sections with zero pre-filled hours. The consultant
fills in hours based on the specific scope of the engagement.
"""


def _pad(hours, n):
    if len(hours) >= n:
        return hours[:n]
    return hours + [0.0] * (n - len(hours))


def _zero(n):
    return [0.0] * n


_SECTIONS = [
    {
        "label": "Onboarding & Discovery",
        "tasks": [
            {"label": "Review of Materials & Background Research"},
            {"label": "Stakeholder Meetings & Onboarding"},
        ],
    },
    {
        "label": "Research & Analysis",
        "tasks": [
            {"label": "Interviews & Information Gathering"},
            {"label": "Analysis & Comparative Research"},
        ],
    },
    {
        "label": "Recommendations & Deliverables",
        "tasks": [
            {"label": "Development of Recommendations"},
            {"label": "Preparation of Deliverables (Report / Presentation / Model)"},
            {"label": "Revisions"},
        ],
    },
    {
        "label": "Stakeholder Engagement & Presentations",
        "tasks": [
            {"label": "Leadership / Board Meetings"},
            {"label": "Follow-up & Implementation Support"},
        ],
    },
]

SCOPE_LABELS = ["Custom"]


def get_sections(scope, team_members, num_months):
    """
    Returns blank sections (all zero hours) for all team members.
    The consultant fills in hours directly in the generated Excel.
    """
    sections = []
    zeros = _zero(num_months)

    for raw_sec in _SECTIONS:
        tasks = []
        for t in raw_sec["tasks"]:
            members = {m["name"]: zeros[:] for m in team_members}
            tasks.append({"label": t["label"], "members": members})
        sections.append({"label": raw_sec["label"], "tasks": tasks})

    return sections


def default_months(scope="Custom"):
    return 4
