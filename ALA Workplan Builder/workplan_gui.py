"""
ALA Workplan Builder — GUI
Run: python workplan_gui.py
"""

import json
import os
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from datetime import datetime

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from generate_workplan import build_workplan
import templates.strategic_plan       as _tmpl_sp
import templates.development_assessment as _tmpl_da
import templates.strategic_counsel     as _tmpl_sc

# Map engagement type label → template module
_TEMPLATES = {
    "Strategic Planning":              _tmpl_sp,
    "Development Department Assessment": _tmpl_da,
    "Strategic Counsel":               _tmpl_sc,
}
ENGAGEMENT_TYPES = list(_TEMPLATES.keys())

_PROJECT_TITLES = {
    "Strategic Planning":              "Strategic Plan",
    "Development Department Assessment": "Development Department Assessment",
    "Strategic Counsel":               "Strategic Counsel",
}

# ---------------------------------------------------------------------------
# Persistent settings
# ---------------------------------------------------------------------------

SETTINGS_PATH = os.path.join(os.path.expanduser("~"), ".ala_workplan", "settings.json")


def load_settings():
    try:
        with open(SETTINGS_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def save_settings(data):
    os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
    with open(SETTINGS_PATH, "w") as f:
        json.dump(data, f, indent=2)


# ---------------------------------------------------------------------------
# Main application
# ---------------------------------------------------------------------------

class WorkplanApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ALA Workplan Builder")
        self.resizable(True, True)
        self.geometry("620x780")

        self._settings = load_settings()
        self._team_rows        = []   # {frame, name, role, rate}
        self._trips            = []   # list of trip dicts (see _add_trip)
        self._consultant_airfare = {}  # name → last-used airfare amount

        self._build_ui()
        self._restore_settings()

    # ── UI construction ──────────────────────────────────────────────────────

    def _build_ui(self):
        # ── Header ──────────────────────────────────────────────────────────
        hdr = tk.Frame(self, bg="#1F3864")
        hdr.pack(fill="x")
        tk.Label(hdr, text="Amplify Leadership Advisors",
                 font=("Arial", 13, "bold"), fg="white", bg="#1F3864",
                 pady=10).pack()

        # ── Scrollable body ──────────────────────────────────────────────────
        body = tk.Frame(self)
        body.pack(fill="both", expand=True)

        self._canvas = tk.Canvas(body, highlightthickness=0)
        vscroll = ttk.Scrollbar(body, orient="vertical",
                                command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=vscroll.set)
        vscroll.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)

        outer = tk.Frame(self._canvas, padx=18, pady=12)
        self._scroll_win = self._canvas.create_window(
            (0, 0), window=outer, anchor="nw")

        # Resize canvas scroll region when content changes
        outer.bind("<Configure>",
                   lambda e: self._canvas.configure(
                       scrollregion=self._canvas.bbox("all")))
        # Stretch inner frame to canvas width
        self._canvas.bind("<Configure>",
                          lambda e: self._canvas.itemconfig(
                              self._scroll_win, width=e.width))
        # Mouse-wheel scrolling
        self._canvas.bind_all("<MouseWheel>",
                              lambda e: self._canvas.yview_scroll(
                                  -1 if e.delta > 0 else 1, "units"))

        # ── Project Info ─────────────────────────────────────────────────────
        self._section_label(outer, "Project Information")

        info = tk.Frame(outer)
        info.pack(fill="x", pady=(0, 6))

        self._lbl(info, "Engagement Type:", 0, 0)
        self._engagement_var = tk.StringVar(value="Strategic Planning")
        ttk.Combobox(info, textvariable=self._engagement_var, width=30,
                     values=ENGAGEMENT_TYPES, state="readonly"
                     ).grid(row=0, column=1, sticky="w", padx=6, pady=3)
        self._engagement_var.trace_add("write", self._on_engagement_change)

        self._lbl(info, "Client Name:", 1, 0)
        self._client_var = tk.StringVar()
        tk.Entry(info, textvariable=self._client_var, width=30
                 ).grid(row=1, column=1, sticky="w", padx=6, pady=3)

        self._lbl(info, "Project Title:", 2, 0)
        self._title_var = tk.StringVar(value="Strategic Plan")
        tk.Entry(info, textvariable=self._title_var, width=30
                 ).grid(row=2, column=1, sticky="w", padx=6, pady=3)

        self._lbl(info, "Start Month (YYYY-MM):", 3, 0)
        self._start_var = tk.StringVar(value=datetime.today().strftime("%Y-%m"))
        tk.Entry(info, textvariable=self._start_var, width=12
                 ).grid(row=3, column=1, sticky="w", padx=6, pady=3)

        self._lbl(info, "Duration (months):", 4, 0)
        self._months_var = tk.IntVar(value=8)
        tk.Spinbox(info, from_=1, to=24, textvariable=self._months_var,
                   width=5).grid(row=4, column=1, sticky="w", padx=6, pady=3)

        self._lbl(info, "Scope:", 5, 0)
        self._scope_frame = tk.Frame(info)
        self._scope_frame.grid(row=5, column=1, sticky="w", padx=6, pady=3)
        self._scope_var = tk.StringVar(value="Medium")
        self._scope_radios = []
        self._rebuild_scope_radios("Strategic Planning")

        # ── Team Members ─────────────────────────────────────────────────────
        self._section_label(outer, "Team Members")

        team_outer = tk.Frame(outer)
        team_outer.pack(fill="x", pady=(0, 4))

        hrow = tk.Frame(team_outer)
        hrow.pack(fill="x")
        for txt, w in [("Name", 18), ("Role", 16), ("Rate ($/hr)", 10)]:
            tk.Label(hrow, text=txt, font=("Arial", 9, "bold"), width=w,
                     anchor="w").pack(side="left", padx=3)

        self._team_frame = tk.Frame(team_outer)
        self._team_frame.pack(fill="x")

        tk.Button(outer, text="+ Add Team Member",
                  command=self._add_team_row, relief="flat",
                  fg="#2E75B6", font=("Arial", 9, "underline")
                  ).pack(anchor="w", pady=(0, 8))

        # ── Travel ───────────────────────────────────────────────────────────
        self._section_label(outer, "Travel")

        # Global rates
        rates_frame = tk.Frame(outer)
        rates_frame.pack(fill="x", pady=(0, 4))
        self._lbl(rates_frame, "Housing rate ($/night):", 0, 0)
        self._housing_rate = tk.IntVar(value=200)
        tk.Spinbox(rates_frame, from_=0, to=9999,
                   textvariable=self._housing_rate, width=7,
                   command=self._update_travel_preview
                   ).grid(row=0, column=1, sticky="w", padx=6, pady=2)
        self._lbl(rates_frame, "Meals & incidentals rate ($/day):", 1, 0)
        self._meals_rate = tk.IntVar(value=75)
        tk.Spinbox(rates_frame, from_=0, to=9999,
                   textvariable=self._meals_rate, width=7,
                   command=self._update_travel_preview
                   ).grid(row=1, column=1, sticky="w", padx=6, pady=2)

        # Container for dynamic trip blocks
        self._trips_frame = tk.Frame(outer)
        self._trips_frame.pack(fill="x", pady=(4, 0))

        tk.Button(outer, text="+ Add Trip",
                  command=self._add_trip, relief="flat",
                  fg="#2E75B6", font=("Arial", 9, "underline")
                  ).pack(anchor="w", pady=(4, 0))

        refresh_row = tk.Frame(outer)
        refresh_row.pack(fill="x", pady=(4, 0))
        tk.Button(refresh_row, text="↻ Refresh Consultant List",
                  command=self._refresh_travel_rows, relief="flat",
                  fg="#2E75B6", font=("Arial", 9, "underline")
                  ).pack(side="left")

        self._travel_preview = tk.Label(refresh_row, text="",
                                        fg="#555555", font=("Arial", 9, "italic"))
        self._travel_preview.pack(side="left", padx=12)

        # ── Admin Fee ─────────────────────────────────────────────────────────
        self._section_label(outer, "Administrative Fee")
        fee_frame = tk.Frame(outer)
        fee_frame.pack(fill="x", pady=(0, 8))
        self._lbl(fee_frame, "Admin fee (%):", 0, 0)
        self._admin_var = tk.DoubleVar(value=3.0)
        tk.Entry(fee_frame, textvariable=self._admin_var, width=8
                 ).grid(row=0, column=1, sticky="w", padx=6, pady=2)

        # ── Output ───────────────────────────────────────────────────────────
        self._section_label(outer, "Output")
        out_frame = tk.Frame(outer)
        out_frame.pack(fill="x", pady=(0, 10))
        self._out_var = tk.StringVar()
        tk.Entry(out_frame, textvariable=self._out_var, width=38
                 ).grid(row=0, column=0, padx=(0, 6), pady=2)
        tk.Button(out_frame, text="Browse…", command=self._browse_output
                  ).grid(row=0, column=1, pady=2)

        # ── Generate ─────────────────────────────────────────────────────────
        tk.Button(outer, text="Generate Workplan",
                  font=("Arial", 11, "bold"), bg="#1F3864", fg="white",
                  activebackground="#2E75B6", relief="flat",
                  padx=16, pady=8, command=self._generate
                  ).pack(fill="x", pady=(4, 0))

        self._status = tk.Label(outer, text="", fg="#333333", font=("Arial", 9))
        self._status.pack(pady=(6, 0))

        # Seed default team rows (trips initialised in _restore_settings)
        self._add_team_row("", "Lead Consultant", "")
        self._add_team_row("", "Associate Consultant", "")

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _section_label(self, parent, text):
        tk.Label(parent, text=text, font=("Arial", 10, "bold"),
                 fg="#1F3864").pack(anchor="w", pady=(10, 2))
        ttk.Separator(parent, orient="horizontal").pack(fill="x", pady=(0, 4))

    def _lbl(self, parent, text, row, col):
        tk.Label(parent, text=text, anchor="e", width=30
                 ).grid(row=row, column=col, sticky="e", padx=(0, 2), pady=2)

    def _add_team_row(self, name="", role="", rate=""):
        frame = tk.Frame(self._team_frame)
        frame.pack(fill="x", pady=1)

        name_var = tk.StringVar(value=name)
        role_var = tk.StringVar(value=role)
        rate_var = tk.StringVar(value=str(rate))

        tk.Entry(frame, textvariable=name_var, width=20).pack(side="left", padx=3)
        tk.Entry(frame, textvariable=role_var, width=18).pack(side="left", padx=3)
        tk.Entry(frame, textvariable=rate_var, width=10).pack(side="left", padx=3)

        row_data = {"frame": frame, "name": name_var, "role": role_var, "rate": rate_var}
        self._team_rows.append(row_data)

        def remove():
            self._team_rows.remove(row_data)
            frame.destroy()

        tk.Button(frame, text="✕", command=remove, relief="flat",
                  fg="#999999", font=("Arial", 9)).pack(side="left")

    def _add_trip(self, trip_data=None):
        """Add a new trip LabelFrame block to the UI."""
        idx = len(self._trips) + 1
        frame = tk.LabelFrame(self._trips_frame,
                              text=f"Trip {idx}",
                              padx=8, pady=6,
                              font=("Arial", 9, "bold"))
        frame.pack(fill="x", pady=4)

        top = tk.Frame(frame)
        top.pack(fill="x")

        # Trip label entry
        tk.Label(top, text="Label:", anchor="e", width=12
                 ).grid(row=0, column=0, sticky="e", padx=(0, 4), pady=2)
        default_label = (trip_data.get("label", f"Trip {idx}")
                         if trip_data else f"Trip {idx}")
        label_var = tk.StringVar(value=default_label)
        tk.Entry(top, textvariable=label_var, width=28
                 ).grid(row=0, column=1, sticky="w", padx=4, pady=2)

        # Nights spinbox
        tk.Label(top, text="Nights:", anchor="e", width=12
                 ).grid(row=1, column=0, sticky="e", padx=(0, 4), pady=2)
        nights_var = tk.IntVar(
            value=trip_data.get("nights", 2) if trip_data else 2)
        tk.Spinbox(top, from_=0, to=60, textvariable=nights_var, width=5,
                   command=self._update_travel_preview
                   ).grid(row=1, column=1, sticky="w", padx=4, pady=2)

        # Meal days spinbox
        tk.Label(top, text="Meal days:", anchor="e", width=12
                 ).grid(row=2, column=0, sticky="e", padx=(0, 4), pady=2)
        meal_days_var = tk.IntVar(
            value=trip_data.get("meal_days", 3) if trip_data else 3)
        tk.Spinbox(top, from_=0, to=60, textvariable=meal_days_var, width=5,
                   command=self._update_travel_preview
                   ).grid(row=2, column=1, sticky="w", padx=4, pady=2)

        # Consultant rows header
        hdr = tk.Frame(frame)
        hdr.pack(fill="x", pady=(8, 2))
        for txt, w in [("Consultant", 20), ("Travels?", 9), ("Airfare ($)", 12)]:
            tk.Label(hdr, text=txt, font=("Arial", 8, "bold"),
                     width=w, anchor="w").pack(side="left", padx=2)

        # Container for per-consultant rows
        consult_frame = tk.Frame(frame)
        consult_frame.pack(fill="x")

        trip_dict = {
            "frame":           frame,
            "label_var":       label_var,
            "nights_var":      nights_var,
            "meal_days_var":   meal_days_var,
            "consult_frame":   consult_frame,
            "consultant_rows": [],
        }
        self._trips.append(trip_dict)

        def remove_trip():
            self._trips.remove(trip_dict)
            frame.destroy()
            self._update_travel_preview()

        tk.Button(top, text="Remove Trip", command=remove_trip,
                  relief="flat", fg="#CC0000", font=("Arial", 8)
                  ).grid(row=0, column=2, sticky="w", padx=10)

        # Populate consultant rows from saved data
        saved_travelers = {}
        if trip_data:
            for t in trip_data.get("travelers", []):
                saved_travelers[t["name"]] = t
        self._populate_trip_consultants(trip_dict, saved_travelers)
        self._update_travel_preview()
        return trip_dict

    def _populate_trip_consultants(self, trip_dict, saved_travelers=None):
        """Rebuild consultant rows for a single trip block."""
        for cr in trip_dict["consultant_rows"]:
            cr["row_frame"].destroy()
        trip_dict["consultant_rows"] = []

        if saved_travelers is None:
            saved_travelers = {}

        for team_row in self._team_rows:
            name = team_row["name"].get().strip()
            if not name:
                continue

            saved = saved_travelers.get(name, {})
            default_airfare = self._consultant_airfare.get(name, 600)

            row_frame = tk.Frame(trip_dict["consult_frame"])
            row_frame.pack(fill="x", pady=1)

            travels_var = tk.BooleanVar(
                value=saved.get("travels", True) if saved else True)
            airfare_var = tk.IntVar(
                value=saved.get("airfare", default_airfare) if saved else default_airfare)

            tk.Label(row_frame, text=name, width=22, anchor="w"
                     ).pack(side="left", padx=2)
            tk.Checkbutton(row_frame, variable=travels_var,
                           command=self._update_travel_preview
                           ).pack(side="left", padx=6)
            e = tk.Entry(row_frame, textvariable=airfare_var, width=10)
            e.pack(side="left", padx=2)
            e.bind("<KeyRelease>", lambda _e: self._update_travel_preview())
            e.bind("<FocusOut>",   lambda _e: self._update_travel_preview())

            trip_dict["consultant_rows"].append({
                "name":      name,
                "travels":   travels_var,
                "airfare":   airfare_var,
                "row_frame": row_frame,
            })

    def _refresh_travel_rows(self):
        """Rebuild consultant rows in all trips after team list changes."""
        for trip in self._trips:
            # Snapshot values and update airfare defaults before rebuilding
            saved = {}
            for cr in trip["consultant_rows"]:
                self._consultant_airfare[cr["name"]] = cr["airfare"].get()
                saved[cr["name"]] = {
                    "travels": cr["travels"].get(),
                    "airfare": cr["airfare"].get(),
                }
            self._populate_trip_consultants(trip, saved)
        self._update_travel_preview()

    def _update_travel_preview(self):
        try:
            housing_rate = self._housing_rate.get()
            meals_rate   = self._meals_rate.get()
            total = 0
            for trip in self._trips:
                nights    = trip["nights_var"].get()
                meal_days = trip["meal_days_var"].get()
                for cr in trip["consultant_rows"]:
                    if cr["travels"].get():
                        total += (cr["airfare"].get()
                                  + nights * housing_rate
                                  + meal_days * meals_rate)
            self._travel_preview.config(
                text=f"Estimated travel total: ${total:,.0f}")
        except Exception:
            self._travel_preview.config(text="")

    def _rebuild_scope_radios(self, engagement):
        """Replace the scope radio buttons to match the selected engagement type."""
        for rb in self._scope_radios:
            rb.destroy()
        self._scope_radios = []
        tmpl = _TEMPLATES[engagement]
        for label in tmpl.SCOPE_LABELS:
            rb = tk.Radiobutton(self._scope_frame, text=label,
                                variable=self._scope_var, value=label,
                                command=self._on_scope_change)
            rb.pack(side="left", padx=(0, 10))
            self._scope_radios.append(rb)
        # Set scope to first valid option for this engagement
        if self._scope_var.get() not in tmpl.SCOPE_LABELS:
            self._scope_var.set(tmpl.SCOPE_LABELS[0])

    def _on_engagement_change(self, *_):
        engagement = self._engagement_var.get()
        self._title_var.set(_PROJECT_TITLES.get(engagement, engagement))
        self._rebuild_scope_radios(engagement)
        self._on_scope_change()

    def _on_scope_change(self):
        tmpl = _TEMPLATES[self._engagement_var.get()]
        self._months_var.set(tmpl.default_months(self._scope_var.get()))

    def _browse_output(self):
        client  = self._client_var.get().strip().replace(" ", "_") or "Workplan"
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            initialfile=f"{client}_Workplan.xlsx",
        )
        if path:
            self._out_var.set(path)

    # ── Settings persistence ─────────────────────────────────────────────────

    def _restore_settings(self):
        s = self._settings
        if "team" in s:
            for row in list(self._team_rows):
                self._team_rows.remove(row)
                row["frame"].destroy()
            for m in s["team"]:
                self._add_team_row(m.get("name", ""), m.get("role", ""),
                                   m.get("rate", ""))
        if "admin_fee_pct" in s:
            self._admin_var.set(s["admin_fee_pct"])
        if "housing_per_night" in s:
            self._housing_rate.set(s["housing_per_night"])
        if "meals_per_day" in s:
            self._meals_rate.set(s["meals_per_day"])
        self._consultant_airfare = s.get("consultant_airfare", {})

        for trip_data in s.get("trips", []):
            self._add_trip(trip_data)
        if not self._trips:
            self._add_trip()  # default empty trip on first run

    def _collect_settings(self):
        # Update airfare defaults from current trip rows
        for trip in self._trips:
            for cr in trip["consultant_rows"]:
                self._consultant_airfare[cr["name"]] = cr["airfare"].get()

        team = []
        for row in self._team_rows:
            name = row["name"].get().strip()
            role = row["role"].get().strip()
            try:
                rate = float(row["rate"].get())
            except ValueError:
                rate = 0
            if name:
                team.append({"name": name, "role": role, "rate": rate})

        trips_data = []
        for trip in self._trips:
            travelers = []
            for cr in trip["consultant_rows"]:
                travelers.append({
                    "name":    cr["name"],
                    "travels": cr["travels"].get(),
                    "airfare": cr["airfare"].get(),
                })
            trips_data.append({
                "label":     trip["label_var"].get().strip(),
                "nights":    trip["nights_var"].get(),
                "meal_days": trip["meal_days_var"].get(),
                "travelers": travelers,
            })

        return {
            "team":               team,
            "admin_fee_pct":      self._admin_var.get(),
            "housing_per_night":  self._housing_rate.get(),
            "meals_per_day":      self._meals_rate.get(),
            "consultant_airfare": self._consultant_airfare,
            "trips":              trips_data,
        }

    # ── Generate ─────────────────────────────────────────────────────────────

    def _generate(self):
        client = self._client_var.get().strip()
        if not client:
            messagebox.showerror("Missing field", "Please enter a client name.")
            return

        start = self._start_var.get().strip()
        try:
            datetime.strptime(start, "%Y-%m")
        except ValueError:
            messagebox.showerror("Invalid date",
                                 "Start month must be in YYYY-MM format.")
            return

        output = self._out_var.get().strip()
        if not output:
            messagebox.showerror("Missing field",
                                 "Please choose an output file location.")
            return

        team = []
        for row in self._team_rows:
            name = row["name"].get().strip()
            role = row["role"].get().strip()
            try:
                rate = float(row["rate"].get())
            except ValueError:
                rate = 0
            if name:
                team.append({"name": name, "role": role, "rate": rate})

        if not team:
            messagebox.showerror("No team members",
                                 "Add at least one team member.")
            return

        # Build travel config from current trip blocks
        travel_cfg = None
        trips_out = []
        for trip in self._trips:
            travelers = [
                {"name": cr["name"], "airfare": cr["airfare"].get()}
                for cr in trip["consultant_rows"]
                if cr["travels"].get()
            ]
            if travelers:
                trips_out.append({
                    "label":     trip["label_var"].get().strip() or "Trip",
                    "nights":    trip["nights_var"].get(),
                    "meal_days": trip["meal_days_var"].get(),
                    "travelers": travelers,
                })
        if trips_out:
            travel_cfg = {
                "housing_per_night": self._housing_rate.get(),
                "meals_per_day":     self._meals_rate.get(),
                "trips":             trips_out,
            }

        tmpl       = _TEMPLATES[self._engagement_var.get()]
        num_months = self._months_var.get()
        cfg = {
            "client_name":   client,
            "project_title": self._title_var.get().strip() or self._engagement_var.get(),
            "team":          team,
            "num_months":    num_months,
            "start_month":   start,
            "admin_fee_pct": self._admin_var.get(),
            "travel":        travel_cfg,
            "sections":      tmpl.get_sections(self._scope_var.get(), team, num_months),
        }

        try:
            build_workplan(cfg, output)
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        save_settings(self._collect_settings())
        self._status.config(text=f"Saved: {os.path.basename(output)}", fg="#1F6B1F")

        if messagebox.askyesno("Done",
                               f"Workplan saved.\n\nOpen {os.path.basename(output)} now?"):
            try:
                os.startfile(output)
            except Exception:
                subprocess.Popen(["open", output])


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app = WorkplanApp()
    app.mainloop()
