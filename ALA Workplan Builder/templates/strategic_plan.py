"""
Strategic Planning engagement templates.

Three scope tiers derived from 7 real ALA workplans:
  Small  — 5–6 months  (e.g. Everyman Theatre)
  Medium — 7–8 months  (e.g. McCarter, City Theatre)
  Large  — 9–10 months (e.g. SCR, ZACH, Writers Theatre)

Hours are indexed to two roles: "lead" and "junior".
When building the config, lead = first team member, junior = second.
Additional team members start with all-zero hours (user fills in Excel).

Each task entry:
  {
    "label": str,
    "lead":  [h_month1, h_month2, ...],   # length == num_months for that tier
    "junior": [h_month1, ...] or None      # None → row omitted for that role
  }
"""


def _pad(hours, n):
    """Extend or truncate a monthly hour list to exactly n months."""
    if len(hours) >= n:
        return hours[:n]
    return hours + [0.0] * (n - len(hours))


def _build_sections(raw_sections, lead_name, junior_name, num_months):
    """
    Convert raw template sections into the config format expected by
    generate_workplan.py, adapting month arrays to num_months.
    """
    sections = []
    for raw_sec in raw_sections:
        tasks = []
        for t in raw_sec["tasks"]:
            if t.get("type") == "interview":
                tasks.append({
                    "label":                 t["label"],
                    "type":                  "interview",
                    "default_num_interviews": t.get("default_num_interviews", 15),
                    "default_hours_per":      t.get("default_hours_per", 1.5),
                })
            else:
                members = {}
                lead_hrs = _pad(t["lead"], num_months)
                members[lead_name] = lead_hrs
                if junior_name and t.get("junior") is not None:
                    junior_hrs = _pad(t["junior"], num_months)
                    members[junior_name] = junior_hrs
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
                "label": "Internal Team Meetings",
                "recurring": True,
                "lead":   [2.0, 2.0, 2.0, 2.0, 2.0, 2.0],
                "junior": [2.0, 2.0, 2.0, 2.0, 2.0, 2.0],
            },
            {
                "label": "Client Check-in Meetings",
                "recurring": True,
                "lead":   [2.0, 2.0, 2.0, 2.0, 2.0, 0.0],
                "junior": [2.0, 2.0, 2.0, 2.0, 2.0, 0.0],
            },
        ],
    },
    {
        "label": "Onboarding & Planning",
        "tasks": [
            {
                "label": "Onboarding and Project Setup",
                "lead":   [4.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                "junior": [4.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            },
        ],
    },
    {
        "label": "Full Day Planning Retreat",
        "tasks": [
            {
                "label": "Planning Retreat (Prep + Facilitation)",
                "lead":   [0.0, 10.0, 0.0, 0.0, 0.0, 0.0],
                "junior": [0.0, 4.0,  0.0, 0.0, 0.0, 0.0],
            },
        ],
    },
    {
        "label": "Discovery & Interviews",
        "tasks": [
            {
                "label": "Review of Existing Materials",
                "lead":   [2.0, 2.0, 0.0, 0.0, 0.0, 0.0],
                "junior": [4.0, 4.0, 0.0, 0.0, 0.0, 0.0],
            },
            {
                "label": "One-on-one Interviews",
                "type":  "interview",
                "default_num_interviews": 12,
                "default_hours_per": 1.5,
            },
        ],
    },
    {
        "label": "SWOT Analysis & Writing",
        "tasks": [
            {
                "label": "SWOT Analysis & Summary of Findings",
                "lead":   [0.0, 0.0, 5.0, 0.0, 0.0, 0.0],
                "junior": [0.0, 0.0, 12.0, 0.0, 0.0, 0.0],
            },
        ],
    },
    {
        "label": "Plan Drafting",
        "tasks": [
            {
                "label": "Draft Strategic Plan",
                "lead":   [0.0, 0.0, 0.0, 6.0, 4.0, 0.0],
                "junior": [0.0, 0.0, 0.0, 8.0, 6.0, 0.0],
            },
        ],
    },
    {
        "label": "Alignment & Final Delivery",
        "tasks": [
            {
                "label": "Alignment Sessions",
                "lead":   [0.0, 0.0, 0.0, 0.0, 4.0, 2.0],
                "junior": [0.0, 0.0, 0.0, 0.0, 2.0, 2.0],
            },
            {
                "label": "Delivery of Final Plan",
                "lead":   [0.0, 0.0, 0.0, 0.0, 0.0, 4.0],
                "junior": [0.0, 0.0, 0.0, 0.0, 0.0, 2.0],
            },
        ],
    },
    {
        "label": "Contract Administration",
        "tasks": [
            {
                "label": "Contract Administration & Communications",
                "lead":   [4.0, 0.75, 0.75, 0.75, 0.75, 0.75],
                "junior": [2.0, 0.25, 0.25, 0.25, 0.25, 0.25],
            },
        ],
    },
]

_MEDIUM_SECTIONS = [
    {
        "label": "Recurring Meetings",
        "tasks": [
            {
                "label": "Internal Team Meetings",
                "recurring": True,
                "lead":   [3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0],
                "junior": [3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0],
            },
            {
                "label": "Client Check-in Meetings",
                "recurring": True,
                "lead":   [2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 0.0],
                "junior": [2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 0.0],
            },
        ],
    },
    {
        "label": "Onboarding & Planning",
        "tasks": [
            {
                "label": "Onboarding and Project Setup",
                "lead":   [6.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                "junior": [6.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            },
        ],
    },
    {
        "label": "Discovery & Deep Data Gathering",
        "tasks": [
            {
                "label": "Review of Existing Materials",
                "lead":   [4.0, 2.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                "junior": [8.0, 4.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            },
            {
                "label": "One-on-one Interviews",
                "type":  "interview",
                "default_num_interviews": 20,
                "default_hours_per": 1.5,
            },
        ],
    },
    {
        "label": "SWOT, Landscape Analysis & Key Trends",
        "tasks": [
            {
                "label": "SWOT Analysis & Summary of Findings",
                "lead":   [0.0, 0.0, 6.0, 4.0, 0.0, 0.0, 0.0, 0.0],
                "junior": [0.0, 0.0, 12.0, 8.0, 0.0, 0.0, 0.0, 0.0],
            },
        ],
    },
    {
        "label": "Vision + Strategies Workshop",
        "tasks": [
            {
                "label": "Vision + Strategies Workshop (Prep + Facilitation)",
                "lead":   [0.0, 0.0, 0.0, 10.0, 0.0, 0.0, 0.0, 0.0],
                "junior": [0.0, 0.0, 0.0, 10.0, 0.0, 0.0, 0.0, 0.0],
            },
        ],
    },
    {
        "label": "Strategic Initiatives & Virtual Workshops",
        "tasks": [
            {
                "label": "Strategic Initiatives (Virtual Workshops)",
                "lead":   [0.0, 0.0, 0.0, 0.0, 8.0, 8.0, 0.0, 0.0],
                "junior": [0.0, 0.0, 0.0, 0.0, 8.0, 8.0, 0.0, 0.0],
            },
            {
                "label": "Board Retreat",
                "lead":   [0.0, 0.0, 0.0, 0.0, 0.0, 4.0, 4.0, 0.0],
                "junior": [0.0, 0.0, 0.0, 0.0, 0.0, 4.0, 4.0, 0.0],
            },
        ],
    },
    {
        "label": "Plan Drafting",
        "tasks": [
            {
                "label": "Draft Strategic Plan",
                "lead":   [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 6.0, 4.0],
                "junior": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 8.0, 6.0],
            },
        ],
    },
    {
        "label": "Final Plan Delivery",
        "tasks": [
            {
                "label": "Delivery of Final Plan & Board Presentation",
                "lead":   [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 6.0],
                "junior": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 6.0],
            },
        ],
    },
    {
        "label": "Contract Administration",
        "tasks": [
            {
                "label": "Contract Administration & Communications",
                "lead":   [6.0, 0.75, 0.75, 0.75, 0.75, 0.75, 0.75, 0.75],
                "junior": [2.0, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25],
            },
        ],
    },
]

_LARGE_SECTIONS = [
    {
        "label": "Recurring Meetings",
        "tasks": [
            {
                "label": "Internal Team Meetings",
                "recurring": True,
                "lead":   [4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0],
                "junior": [4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0],
            },
            {
                "label": "Client Check-in Meetings",
                "recurring": True,
                "lead":   [2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 0.0],
                "junior": [2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 0.0],
            },
        ],
    },
    {
        "label": "Phase One: Discovery & Planning",
        "tasks": [
            {
                "label": "Onboarding and Project Setup",
                "lead":   [6.0, 2.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                "junior": [10.0, 2.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            },
            {
                "label": "Review of Existing Materials",
                "lead":   [0.0, 4.0, 2.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                "junior": [0.0, 8.0, 4.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            },
        ],
    },
    {
        "label": "Phase Two: Interviews & SWOT",
        "tasks": [
            {
                "label": "One-on-one Interviews",
                "type":  "interview",
                "default_num_interviews": 30,
                "default_hours_per": 1.5,
            },
            {
                "label": "SWOT Writing & Summary of Findings",
                "lead":   [0.0, 0.0, 0.0, 6.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                "junior": [0.0, 0.0, 0.0, 20.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            },
        ],
    },
    {
        "label": "Phase Three: Vision, Mission & Values",
        "tasks": [
            {
                "label": "Vision/Mission/Values Retreat & Follow-up",
                "lead":   [0.0, 0.0, 0.0, 0.0, 16.0, 4.0, 0.0, 0.0, 0.0, 0.0],
                "junior": [0.0, 0.0, 0.0, 0.0, 16.0, 4.0, 0.0, 0.0, 0.0, 0.0],
            },
        ],
    },
    {
        "label": "Phase Four: Strategic Initiatives",
        "tasks": [
            {
                "label": "Strategic Initiatives Development",
                "lead":   [0.0, 0.0, 0.0, 0.0, 0.0, 12.0, 12.0, 0.0, 0.0, 0.0],
                "junior": [0.0, 0.0, 0.0, 0.0, 0.0, 12.0, 12.0, 0.0, 0.0, 0.0],
            },
        ],
    },
    {
        "label": "Phase Five: Tactics & Financial Modeling",
        "tasks": [
            {
                "label": "Tactics & Financial Modeling",
                "lead":   [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 10.0, 10.0, 0.0],
                "junior": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 14.0, 14.0, 0.0],
            },
            {
                "label": "Final Tactical & Alignment Retreat",
                "lead":   [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 12.0, 8.0],
                "junior": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 20.0, 8.0],
            },
        ],
    },
    {
        "label": "Phase Six: Final Writing & Delivery",
        "tasks": [
            {
                "label": "Final Plan Writing",
                "lead":   [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 10.0],
                "junior": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 20.0],
            },
            {
                "label": "Delivery of Final Plan & Board Presentation",
                "lead":   [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 8.0],
                "junior": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 8.0],
            },
        ],
    },
    {
        "label": "Contract Administration",
        "tasks": [
            {
                "label": "Contract Administration & Communications",
                "lead":   [6.0, 0.75, 0.75, 0.75, 0.75, 0.75, 0.75, 0.75, 0.75, 0.75],
                "junior": [2.0, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25],
            },
        ],
    },
]

# Map scope label → (raw sections, default months)
_TEMPLATES = {
    "Small":  (_SMALL_SECTIONS,  6),
    "Medium": (_MEDIUM_SECTIONS, 8),
    "Large":  (_LARGE_SECTIONS, 10),
}

SCOPE_LABELS = list(_TEMPLATES.keys())


def get_sections(scope, team_members, num_months):
    """
    Return fully-built sections list ready for generate_workplan.build_workplan().

    Parameters
    ----------
    scope        : "Small", "Medium", or "Large"
    team_members : list of {name, role, rate} dicts — first is lead, second is junior,
                   any additional members get zero hours (user fills in Excel)
    num_months   : actual project duration (template hours are padded/truncated)
    """
    lead_name   = team_members[0]["name"] if team_members else "Lead"
    junior_name = team_members[1]["name"] if len(team_members) > 1 else None
    extra_names = [m["name"] for m in team_members[2:]]

    raw, _ = _TEMPLATES[scope]
    sections = _build_sections(raw, lead_name, junior_name, num_months)

    # Add extra team members to every task with zero hours so they appear in Excel
    if extra_names:
        zeros = [0.0] * num_months
        for section in sections:
            for task in section["tasks"]:
                if task.get("type") != "interview":  # interview task handles all members itself
                    for name in extra_names:
                        task["members"][name] = zeros[:]

    return sections


def default_months(scope):
    """Return the recommended number of months for a given scope tier."""
    _, n = _TEMPLATES[scope]
    return n
