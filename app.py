"""
ACT Attendee Enrichment Tool — Desktop UI

Run with:
    python app.py
"""

import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path

import config
from enrichment.reader import read_attendees
from enrichment.api import enrich_person
from enrichment.flags import is_csuite, is_hr, is_ld, is_marketing_comms
from enrichment.writer import write_results
from enrichment.column_map import FIELDS, detect, extract_name_and_location


class ColumnMapDialog(tk.Toplevel):
    """
    Shows the columns found in the uploaded file and lets the user
    confirm or correct which column maps to which field.
    Returns a mapping dict, or None if the user cancelled.
    """

    NONE_LABEL = "(not in my file)"

    def __init__(self, parent, headers: list[str], guesses: dict):
        super().__init__(parent)
        self.title("Match Your Columns")
        self.resizable(True, True)
        self.configure(padx=28, pady=20, bg="#f5f5f5")
        self.grab_set()

        self._headers = headers
        self._result = None
        self._vars: dict[str, tk.StringVar] = {}

        self._build(guesses)
        self._center(parent)

        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.wait_window(self)

    # ------------------------------------------------------------------ layout

    def _build(self, guesses: dict):
        bg = "#f5f5f5"

        tk.Label(self, text="Match Your Columns",
                 font=("Segoe UI", 13, "bold"), bg=bg).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 4))

        tk.Label(self,
                 text="We detected the columns in your file. Check that each field\n"
                      "below is matched to the right column, then click Confirm.",
                 font=("Segoe UI", 9), bg=bg, fg="#555", justify="left").grid(
            row=1, column=0, columnspan=3, sticky="w", pady=(0, 14))

        options = [self.NONE_LABEL] + self._headers

        # Each field gets two grid rows: one for the dropdown, one for the hint
        for i, (key, label, required, hint) in enumerate(FIELDS):
            dropdown_row = 2 + i * 2
            hint_row     = dropdown_row + 1

            req_marker = "  *" if required else ""
            tk.Label(self, text=f"{label}{req_marker}", font=("Segoe UI", 10, "bold"),
                     bg=bg, width=18, anchor="w").grid(
                row=dropdown_row, column=0, sticky="w", padx=(0, 8), pady=(6, 0))

            var = tk.StringVar()
            guess = guesses.get(key)
            var.set(guess if guess in self._headers else self.NONE_LABEL)
            self._vars[key] = var

            cb = ttk.Combobox(self, textvariable=var, values=options,
                              state="readonly", width=30, font=("Segoe UI", 10))
            cb.grid(row=dropdown_row, column=1, sticky="w", pady=(6, 0))

            # Green check / red warning indicator
            indicator = tk.Label(self, text="", font=("Segoe UI", 11),
                                 bg=bg, width=2)
            indicator.grid(row=dropdown_row, column=2, sticky="w",
                           padx=(6, 0), pady=(6, 0))

            def make_updater(v, ind, req):
                def update(*_):
                    val = v.get()
                    if val != self.NONE_LABEL:
                        ind.configure(text="\u2713", fg="#107c10")
                    elif req:
                        ind.configure(text="!", fg="#c50000")
                    else:
                        ind.configure(text="", fg=bg)
                return update

            updater = make_updater(var, indicator, required)
            var.trace_add("write", updater)
            updater()

            # Hint on its own row, clearly below the dropdown
            tk.Label(self, text=hint, font=("Segoe UI", 8), bg=bg, fg="#999",
                     anchor="w").grid(row=hint_row, column=1, columnspan=2,
                                      sticky="w", pady=(0, 4))

        sep_row = 2 + len(FIELDS) * 2
        ttk.Separator(self, orient="horizontal").grid(
            row=sep_row, column=0, columnspan=3, sticky="ew", pady=14)

        tk.Label(self, text="* Required fields", font=("Segoe UI", 8),
                 bg=bg, fg="#888").grid(row=sep_row + 1, column=0, sticky="w")

        btn_frame = tk.Frame(self, bg=bg)
        btn_frame.grid(row=sep_row + 2, column=0, columnspan=3, pady=(4, 0))

        tk.Button(btn_frame, text="Confirm  ✓", font=("Segoe UI", 10, "bold"),
                  command=self._confirm, relief="flat",
                  bg="#107c10", fg="white", activebackground="#0a5c0a",
                  activeforeground="white", cursor="hand2",
                  padx=16, pady=7).pack(side="left", padx=(0, 10))

        tk.Button(btn_frame, text="Cancel", font=("Segoe UI", 10),
                  command=self._cancel, relief="flat",
                  bg="#e0e0e0", fg="#333", cursor="hand2",
                  padx=12, pady=7).pack(side="left")

    def _center(self, parent):
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    # ----------------------------------------------------------------- actions

    def _confirm(self):
        # Validate required fields are mapped
        for key, label, required, _ in FIELDS:
            if required and self._vars[key].get() == self.NONE_LABEL:
                messagebox.showwarning(
                    "Required field missing",
                    f'"{label}" is required but not matched to any column.\n'
                    f"Please select the column that contains {label}.",
                    parent=self,
                )
                return

        self._result = {
            key: (v.get() if v.get() != self.NONE_LABEL else None)
            for key, v in self._vars.items()
        }
        self.destroy()

    def _cancel(self):
        self._result = None
        self.destroy()

    @property
    def mapping(self) -> dict | None:
        return self._result


# ---------------------------------------------------------------------------

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ACT Attendee Enrichment Tool")
        self.resizable(False, False)
        self.configure(padx=24, pady=20, bg="#f5f5f5")

        self._input_path = tk.StringVar()
        self._output_path = tk.StringVar()
        self._status = tk.StringVar(value="Select an input file to get started.")
        self._running = False
        self._column_mapping: dict | None = None  # confirmed mapping from dialog

        self._build_ui()
        self._center()
        self._check_api_key()

    # ------------------------------------------------------------------ layout

    def _build_ui(self):
        bg = "#f5f5f5"
        label_font = ("Segoe UI", 10)
        entry_font = ("Segoe UI", 10)
        btn_font = ("Segoe UI", 10, "bold")

        # Title row
        tk.Label(self, text="ACT Attendee Enrichment Tool",
                 font=("Segoe UI", 14, "bold"), bg=bg, fg="#222").grid(
            row=0, column=0, columnspan=2, pady=(0, 16), sticky="w")
        tk.Button(self, text="⚙ Settings", font=("Segoe UI", 9),
                  command=self._open_settings, relief="flat",
                  bg="#f5f5f5", fg="#555", activebackground="#e0e0e0",
                  cursor="hand2").grid(row=0, column=2, pady=(0, 16), sticky="e")

        # Input file
        tk.Label(self, text="Input file (.xlsx):", font=label_font, bg=bg).grid(
            row=1, column=0, sticky="w", pady=4)
        tk.Entry(self, textvariable=self._input_path, width=44,
                 font=entry_font, state="readonly").grid(
            row=1, column=1, padx=8, pady=4)
        tk.Button(self, text="Browse…", font=btn_font, width=9,
                  command=self._pick_input, relief="flat",
                  bg="#0078d4", fg="white", activebackground="#005fa3",
                  activeforeground="white", cursor="hand2").grid(
            row=1, column=2, pady=4)

        # Output file
        tk.Label(self, text="Output file (.xlsx):", font=label_font, bg=bg).grid(
            row=2, column=0, sticky="w", pady=4)
        tk.Entry(self, textvariable=self._output_path, width=44,
                 font=entry_font, state="readonly").grid(
            row=2, column=1, padx=8, pady=4)
        tk.Button(self, text="Browse…", font=btn_font, width=9,
                  command=self._pick_output, relief="flat",
                  bg="#0078d4", fg="white", activebackground="#005fa3",
                  activeforeground="white", cursor="hand2").grid(
            row=2, column=2, pady=4)

        # Column mapping indicator
        self._mapping_label = tk.Label(
            self, text="", font=("Segoe UI", 9), bg=bg, fg="#555")
        self._mapping_label.grid(row=3, column=0, columnspan=3, sticky="w", pady=(2, 0))

        # Separator
        ttk.Separator(self, orient="horizontal").grid(
            row=4, column=0, columnspan=3, sticky="ew", pady=14)

        # Run button
        self._run_btn = tk.Button(
            self, text="▶  Run Enrichment", font=("Segoe UI", 11, "bold"),
            command=self._start, relief="flat", bg="#107c10", fg="white",
            activebackground="#0a5c0a", activeforeground="white",
            cursor="hand2", padx=16, pady=8)
        self._run_btn.grid(row=5, column=0, columnspan=3, pady=(0, 12))

        # Progress bar
        self._progress = ttk.Progressbar(self, length=460, mode="determinate")
        self._progress.grid(row=6, column=0, columnspan=3, pady=(0, 6))

        # Status label
        tk.Label(self, textvariable=self._status, font=("Segoe UI", 9),
                 bg=bg, fg="#555", wraplength=460, justify="left").grid(
            row=7, column=0, columnspan=3, sticky="w")

        # Results box
        self._results = tk.Text(self, height=8, width=58, font=("Consolas", 9),
                                state="disabled", bg="white", relief="solid",
                                borderwidth=1)
        self._results.grid(row=8, column=0, columnspan=3, pady=(12, 0))

    def _center(self):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")

    # ---------------------------------------------------------------- actions

    def _pick_input(self):
        path = filedialog.askopenfilename(
            title="Select attendee spreadsheet",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")])
        if not path:
            return

        # Read headers first
        try:
            rows = read_attendees(path)
        except Exception as e:
            messagebox.showerror("Could not read file", str(e))
            return

        if not rows:
            messagebox.showwarning("Empty file", "That file has no data rows.")
            return

        headers = list(rows[0].keys())
        guesses = detect(headers)

        # Show column mapping dialog
        dialog = ColumnMapDialog(self, headers, guesses)
        if dialog.mapping is None:
            return  # user cancelled

        self._column_mapping = dialog.mapping
        self._input_path.set(path)

        p = Path(path)
        self._output_path.set(str(p.parent / f"{p.stem}_enriched.xlsx"))

        # Show confirmed mapping summary
        first_col = self._column_mapping.get("first_name", "?")
        last_col  = self._column_mapping.get("last_name", "?")
        self._mapping_label.configure(
            text=f"\u2713 Columns mapped  \u2014  Name: '{first_col}' + '{last_col}'",
            fg="#107c10")
        self._status.set("Ready. Click Run Enrichment to begin.")

    def _pick_output(self):
        path = filedialog.asksaveasfilename(
            title="Save output as",
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")])
        if path:
            self._output_path.set(path)

    def _start(self):
        if self._running:
            return
        if not self._input_path.get():
            messagebox.showwarning("No file selected", "Please choose an input Excel file first.")
            return
        if not self._column_mapping:
            messagebox.showwarning("Columns not mapped", "Please select an input file to set up column mapping.")
            return
        self._running = True
        self._run_btn.configure(state="disabled", bg="#888")
        self._clear_results()
        threading.Thread(target=self._run, daemon=True).start()

    # ----------------------------------------------------------------- worker

    def _run(self):
        input_path = self._input_path.get()
        output_path = self._output_path.get() or str(
            Path(input_path).parent / f"{Path(input_path).stem}_enriched.xlsx")

        try:
            attendees = read_attendees(input_path)
        except Exception as e:
            self._finish_error(f"Could not read file:\n{e}")
            return

        total = len(attendees)
        original_headers = list(attendees[0].keys()) if attendees else []
        matched, unmatched, flagged = [], [], 0

        self._progress["maximum"] = total
        self._progress["value"] = 0

        for i, row in enumerate(attendees, start=1):
            first, last, location, email = extract_name_and_location(row, self._column_mapping)

            self._status.set(f"Processing {i} of {total}:  {first} {last}")
            self._progress["value"] = i

            try:
                result = enrich_person(first, last, location, email)
            except Exception:
                result = None

            if result is None:
                unmatched.append(row)
                continue

            enriched = {
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
            if enriched["hr_flag"] or enriched["csuite_flag"] or enriched["ld_flag"] or enriched["marketing_flag"]:
                flagged += 1
            matched.append(enriched)

        try:
            write_results(output_path, original_headers, matched, unmatched)
        except Exception as e:
            self._finish_error(f"Could not write output file:\n{e}")
            return

        self._finish_ok(total, len(matched), len(unmatched), flagged, output_path)

    # --------------------------------------------------------------- callbacks

    def _finish_ok(self, total, matched, unmatched, flagged, output_path):
        self._status.set("Done!")
        summary = (
            f"{'─' * 46}\n"
            f"  Total processed      : {total}\n"
            f"  Matched              : {matched}\n"
            f"  Unmatched            : {unmatched}\n"
            f"  Flagged (HR/C-Suite) : {flagged}\n"
            f"{'─' * 46}\n"
            f"  Output saved to:\n"
            f"  {output_path}\n"
        )
        self._append_results(summary)
        self._running = False
        self._run_btn.configure(state="normal", bg="#107c10")
        messagebox.showinfo("Complete", f"Enrichment finished!\n\nOpening file now...")
        import os
        os.startfile(output_path)

    def _finish_error(self, msg):
        self._status.set("An error occurred.")
        self._append_results(f"ERROR:\n{msg}\n")
        self._running = False
        self._run_btn.configure(state="normal", bg="#107c10")
        messagebox.showerror("Error", msg)

    def _clear_results(self):
        self._results.configure(state="normal")
        self._results.delete("1.0", tk.END)
        self._results.configure(state="disabled")

    def _append_results(self, text):
        self._results.configure(state="normal")
        self._results.insert(tk.END, text)
        self._results.configure(state="disabled")

    # ------------------------------------------------------------ settings

    def _check_api_key(self):
        if not config.get_api_key():
            self._status.set(
                "No API key saved — running in demo mode. "
                "Click ⚙ Settings to add your key when ready."
            )

    def _open_settings(self):
        win = tk.Toplevel(self)
        win.title("Settings")
        win.resizable(False, False)
        win.configure(padx=24, pady=20, bg="#f5f5f5")
        win.grab_set()

        bg = "#f5f5f5"
        current_key = config.get_api_key() or ""

        tk.Label(win, text="API Settings", font=("Segoe UI", 12, "bold"),
                 bg=bg).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))

        tk.Label(win, text="Enrichment API Key:", font=("Segoe UI", 10),
                 bg=bg).grid(row=1, column=0, sticky="w", pady=4)

        key_var = tk.StringVar(value=current_key)
        key_entry = tk.Entry(win, textvariable=key_var, width=36,
                             font=("Segoe UI", 10), show="•")
        key_entry.grid(row=1, column=1, padx=(8, 0), pady=4)

        def toggle_show():
            key_entry.configure(show="" if key_entry.cget("show") == "•" else "•")
        tk.Button(win, text="Show / Hide", font=("Segoe UI", 9),
                  command=toggle_show, relief="flat", bg="#e0e0e0",
                  cursor="hand2").grid(row=2, column=1, sticky="w", padx=(8, 0))

        tk.Label(win,
                 text="Paste your API key above. Leave blank to run in demo mode.",
                 font=("Segoe UI", 8), bg=bg, fg="#777", wraplength=320).grid(
            row=3, column=0, columnspan=2, sticky="w", pady=(8, 12))

        def save():
            new_key = key_var.get().strip()
            if new_key:
                config.set_api_key(new_key)
                messagebox.showinfo("Saved", "API key saved.", parent=win)
            else:
                config.save({})
                messagebox.showinfo("Cleared", "API key removed. App will run in demo mode.", parent=win)
            self._check_api_key()
            win.destroy()

        tk.Button(win, text="Save", font=("Segoe UI", 10, "bold"),
                  command=save, relief="flat", bg="#0078d4", fg="white",
                  activebackground="#005fa3", activeforeground="white",
                  cursor="hand2", padx=12, pady=6).grid(
            row=4, column=0, columnspan=2, pady=(4, 0))

        win.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - win.winfo_width()) // 2
        y = self.winfo_y() + (self.winfo_height() - win.winfo_height()) // 2
        win.geometry(f"+{x}+{y}")


if __name__ == "__main__":
    app = App()
    app.mainloop()
