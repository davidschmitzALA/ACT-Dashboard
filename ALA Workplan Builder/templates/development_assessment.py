"""
Development Department Assessment engagement templates.

Modeled directly from the CTG Institutional Advancement Assessment workplan.

Scope tiers vary primarily by number of interviewees:
  Small  — 3–4 months, ~15 development team interviewees
  Medium — 5 months,   ~30 development team interviewees  (CTG model)
  Large  — 6–7 months, ~50 development team interviewees
"""


def _pad(hours, n):
    if len(hours) >= n:
        return hours[:n]
    return hours + [0.0] * (n - len(hours))


def _build_sections(raw_sections, lead_name, junior_name, num_months):
    sections = []
    for raw_sec in raw_sections:
        tasks = []
        for t in raw_sec["tasks"]:
            if t.get("type") == "interview":
                tasks.append({
                    "label":                  t["label"],
                    "type":                   "interview",
                    "default_num_interviews":  t.get("default_num_interviews", 15),
                    "default_hours_per":       t.get("default_hours_per", 1.0),
                })
            else:
                members = {}
                members[lead_name] = _pad(t["lead"], num_months)
                if junior_name and t.get("junior") is not None:
                    members[junior_name] = _pad(t["junior"], num_months)
                task_dict = {"label": t["label"], "members": members}
                if t.get("recurring"):
                    task_dict["recurring"] = True
                tasks.append(task_dict)
        sections.append({"label": raw_sec["label"], "tasks": tasks})
    return sections


# ---------------------------------------------------------------------------
# RAW TEMPLATE DATA
# ---------------------------------------------------------------------------

_SMALL_SECTIONS = [
    {
        "label": "Recurring Meetings",
        "tasks": [
            {
                "label": "Project Check-in Meetings",
                "recurring": True,
                "lead":   [3.0, 3.0, 3.0, 3.0],
                "junior": [3.0, 3.0, 3.0, 3.0],
            },
        ],
    },
    {
        "label": "Onboarding, Planning & Document Review",
        "tasks": [
            {
                "label": "Onboarding, Planning & Document Review (incl. Job Descriptions)",
                "lead":   [6.0, 0.0, 0.0, 0.0],
                "junior": [6.0, 0.0, 0.0, 0.0],
            },
        ],
    },
    {
        "label": "Interviews — Development Department",
        "tasks": [
            {
                "label": "Interviews — Development Team",
                "type":  "interview",
                "default_num_interviews": 15,
                "default_hours_per": 1.0,
            },
        ],
    },
    {
        "label": "Interviews — Cross-Functional",
        "tasks": [
            {
                "label": "Interviews — Marketing, Finance, IT & Other",
                "type":  "interview",
                "default_num_interviews": 5,
                "default_hours_per": 1.0,
            },
        ],
    },
    {
        "label": "Comparative Analysis",
        "tasks": [
            {
                "label": "Comparative Analysis of Similar Organizations",
                "lead":   [0.0, 2.0, 2.0, 0.0],
                "junior": [0.0, 4.0, 6.0, 0.0],
            },
        ],
    },
    {
        "label": "Report Draft & Revisions",
        "tasks": [
            {
                "label": "Report Draft & Revisions",
                "lead":   [0.0, 0.0, 4.0, 4.0],
                "junior": [0.0, 0.0, 6.0, 8.0],
            },
        ],
    },
    {
        "label": "Reporting to Board & Leadership",
        "tasks": [
            {
                "label": "Reporting to Board & Leadership",
                "lead":   [0.0, 0.0, 0.0, 4.0],
                "junior": [0.0, 0.0, 0.0, 3.0],
            },
        ],
    },
]

_MEDIUM_SECTIONS = [
    {
        "label": "Recurring Meetings",
        "tasks": [
            {
                "label": "Project Check-in Meetings",
                "recurring": True,
                "lead":   [4.0, 4.0, 4.0, 3.0, 1.0],
                "junior": [4.0, 4.0, 4.0, 3.0, 1.0],
            },
        ],
    },
    {
        "label": "Onboarding, Planning & Document Review",
        "tasks": [
            {
                "label": "Onboarding, Planning & Document Review (incl. Job Descriptions)",
                "lead":   [6.0, 0.0, 0.0, 0.0, 0.0],
                "junior": [6.0, 0.0, 0.0, 0.0, 0.0],
            },
        ],
    },
    {
        "label": "Interviews — Development Department",
        "tasks": [
            {
                "label": "Interviews — Development Team",
                "type":  "interview",
                "default_num_interviews": 30,
                "default_hours_per": 1.0,
            },
        ],
    },
    {
        "label": "Interviews — Cross-Functional",
        "tasks": [
            {
                "label": "Interviews — Marketing, Finance, IT & Other",
                "type":  "interview",
                "default_num_interviews": 10,
                "default_hours_per": 1.0,
            },
        ],
    },
    {
        "label": "Comparative Analysis",
        "tasks": [
            {
                "label": "Comparative Analysis of Similar Organizations",
                "lead":   [1.0, 1.0, 1.0, 0.0, 0.0],
                "junior": [4.0, 6.0, 4.0, 0.0, 0.0],
            },
        ],
    },
    {
        "label": "Report Draft & Revisions",
        "tasks": [
            {
                "label": "Report Draft & Revisions",
                "lead":   [0.0, 0.0, 4.0, 4.0, 2.0],
                "junior": [0.0, 0.0, 6.0, 8.0, 4.0],
            },
        ],
    },
    {
        "label": "Reporting to Board & Leadership",
        "tasks": [
            {
                "label": "Reporting to Board & Leadership",
                "lead":   [0.0, 0.0, 0.0, 3.0, 4.0],
                "junior": [0.0, 0.0, 0.0, 2.0, 4.0],
            },
        ],
    },
]

_LARGE_SECTIONS = [
    {
        "label": "Recurring Meetings",
        "tasks": [
            {
                "label": "Project Check-in Meetings",
                "recurring": True,
                "lead":   [4.0, 4.0, 4.0, 4.0, 4.0, 3.0, 1.0],
                "junior": [4.0, 4.0, 4.0, 4.0, 4.0, 3.0, 1.0],
            },
        ],
    },
    {
        "label": "Onboarding, Planning & Document Review",
        "tasks": [
            {
                "label": "Onboarding, Planning & Document Review (incl. Job Descriptions)",
                "lead":   [8.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                "junior": [8.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            },
        ],
    },
    {
        "label": "Interviews — Development Department",
        "tasks": [
            {
                "label": "Interviews — Development Team",
                "type":  "interview",
                "default_num_interviews": 50,
                "default_hours_per": 1.0,
            },
        ],
    },
    {
        "label": "Interviews — Cross-Functional",
        "tasks": [
            {
                "label": "Interviews — Marketing, Finance, IT & Other",
                "type":  "interview",
                "default_num_interviews": 15,
                "default_hours_per": 1.0,
            },
        ],
    },
    {
        "label": "Comparative Analysis",
        "tasks": [
            {
                "label": "Comparative Analysis of Similar Organizations",
                "lead":   [1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0],
                "junior": [4.0, 6.0, 6.0, 4.0, 0.0, 0.0, 0.0],
            },
        ],
    },
    {
        "label": "Report Draft & Revisions",
        "tasks": [
            {
                "label": "Report Draft & Revisions",
                "lead":   [0.0, 0.0, 0.0, 0.0, 6.0, 6.0, 2.0],
                "junior": [0.0, 0.0, 0.0, 0.0, 8.0, 10.0, 4.0],
            },
        ],
    },
    {
        "label": "Reporting to Board & Leadership",
        "tasks": [
            {
                "label": "Reporting to Board & Leadership",
                "lead":   [0.0, 0.0, 0.0, 0.0, 0.0, 4.0, 4.0],
                "junior": [0.0, 0.0, 0.0, 0.0, 0.0, 3.0, 4.0],
            },
        ],
    },
]

_TEMPLATES = {
    "Small":  (_SMALL_SECTIONS,  4),
    "Medium": (_MEDIUM_SECTIONS, 5),
    "Large":  (_LARGE_SECTIONS,  7),
}

SCOPE_LABELS = list(_TEMPLATES.keys())


def get_sections(scope, team_members, num_months):
    lead_name   = team_members[0]["name"] if team_members else "Lead"
    junior_name = team_members[1]["name"] if len(team_members) > 1 else None
    extra_names = [m["name"] for m in team_members[2:]]

    raw, _ = _TEMPLATES[scope]
    sections = _build_sections(raw, lead_name, junior_name, num_months)

    if extra_names:
        zeros = [0.0] * num_months
        for section in sections:
            for task in section["tasks"]:
                if task.get("type") != "interview":
                    for name in extra_names:
                        task["members"][name] = zeros[:]

    return sections


def default_months(scope):
    _, n = _TEMPLATES[scope]
    return n
