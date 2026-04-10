import { useState, useCallback } from "react";
import * as XLSX from "xlsx";

// ─── Default sections based on ALA Strategic Plan template ───────────────────
const DEFAULT_SECTIONS = [
  {
    id: 1,
    label: "Project Management & Meetings",
    tasks: [
      { id: 1, label: "Coordination Meetings" },
      { id: 2, label: "Planning Committee Meetings" },
      { id: 3, label: "Core Team / Leadership Meetings" },
      { id: 4, label: "Contract Administration" },
    ],
  },
  {
    id: 2,
    label: "Discovery & Deep Data Gathering",
    tasks: [
      { id: 5, label: "Review of Existing Materials" },
      { id: 6, label: "One-on-One Interviews" },
      { id: 7, label: "Virtual Focus Groups" },
      { id: 8, label: "Individual Insights Survey" },
      { id: 9, label: "SWOT, Landscape Analysis & Key Trends (AI Assisted)" },
    ],
  },
  {
    id: 3,
    label: "Vision, Values & Strategic Priorities",
    tasks: [
      { id: 10, label: "Community Gathering / Retreat" },
      { id: 11, label: "Follow-Up Meetings for Vision & Strategic Direction" },
    ],
  },
  {
    id: 4,
    label: "Tactical Exploration & Modeling",
    tasks: [{ id: 12, label: "Tactical Development Meetings" }],
  },
  {
    id: 5,
    label: "Strategic Plan Creation & Alignment",
    tasks: [{ id: 13, label: "Plan Writing (AI Assisted)" }],
  },
];

const MONTH_NAMES = [
  "Jan","Feb","Mar","Apr","May","Jun",
  "Jul","Aug","Sep","Oct","Nov","Dec",
];

function getMonthLabels(startMonth, numMonths) {
  if (!startMonth) return Array.from({ length: numMonths }, (_, i) => `Month ${i + 1}`);
  const [year, month] = startMonth.split("-").map(Number);
  return Array.from({ length: numMonths }, (_, i) => {
    const d = new Date(year, month - 1 + i);
    return `${MONTH_NAMES[d.getMonth()]} ${d.getFullYear()}`;
  });
}

// ─── XLSX Generation ──────────────────────────────────────────────────────────
function generateXLSX(config) {
  const { clientName, projectTitle, team, startMonth, numMonths, sections, expenses } = config;
  const monthLabels = getMonthLabels(startMonth, numMonths);

  const wb = XLSX.utils.book_new();
  const wsData = [];

  // Helper: pad array to numMonths
  const padHours = (arr) => {
    const out = [...(arr || [])];
    while (out.length < numMonths) out.push(null);
    return out.slice(0, numMonths);
  };

  // Row 1: Title
  wsData.push([`Amplify Leadership Advisors  |  ${clientName} — ${projectTitle}`]);

  // Row 2: spacer
  wsData.push([]);

  // Row 3: Team header
  wsData.push(["Team Member", "Role", "Rate ($/hr)"]);

  // Rows 4+: Team members
  const teamStartRow = 4;
  team.forEach((m) => {
    wsData.push([m.name, m.role, m.rate]);
  });

  const rateEndRow = teamStartRow + team.length - 1;

  // Spacer
  wsData.push([]);

  // WBS header row
  const wbsHeaderRow = rateEndRow + 3; // 1-indexed in sheet
  wsData.push(["Task / Activity", "Team Member", "Total Cost ($)", "Total Hours", ...monthLabels]);

  // WBS body
  const allTaskRows = []; // {memberName, excelRow} for grand total

  sections.forEach((section) => {
    // Section header
    wsData.push([section.label]);
    const sectionStartDataRow = wbsHeaderRow + wsData.length - (wbsHeaderRow); // track below

    section.tasks.forEach((task) => {
      team.forEach((member) => {
        const monthlyHours = padHours(task.hours?.[member.name] || []);
        wsData.push([
          task.label,
          member.name,
          null, // cost formula placeholder
          null, // hours formula placeholder
          ...monthlyHours,
        ]);
        allTaskRows.push({ memberName: member.name, rowIdx: wsData.length }); // 1-indexed relative
      });
    });

    // Subtotal row
    wsData.push([`Subtotal — ${section.label}`, "", null, null, ...Array(numMonths).fill(null)]);
  });

  // Expenses
  if (expenses && expenses.length > 0) {
    wsData.push(["Expenses & Pass-Through Costs"]);
    expenses.forEach((exp) => {
      wsData.push([exp.label, "", exp.amount, "", ...Array(numMonths).fill(null)]);
    });
    wsData.push(["Subtotal — Expenses", "", null, null, ...Array(numMonths).fill(null)]);
  }

  // Grand total
  wsData.push(["TOTAL PROJECT COST", "", null, null, ...Array(numMonths).fill(null)]);

  // Per-person summary
  wsData.push([]);
  wsData.push(["Team Member", "Role", "Total Cost", "Total Hours"]);
  team.forEach((m) => {
    wsData.push([m.name, m.role, null, null]);
  });

  // ── Build worksheet with proper formulas ──────────────────────────────────
  const ws = XLSX.utils.aoa_to_sheet(wsData);

  // Now go back and write formulas into Cost and Hours cells
  // Row offset: wsData[0] = sheet row 1, etc.
  // We need to find each task row and write: 
  //   D = SUM(E..last_month_col)
  //   C = rate_cell * D
  // and subtotals, grand total

  const COL_A = 0, COL_B = 1, COL_C = 2, COL_D = 3, COL_E = 4;

  function cellAddr(row1indexed, col0indexed) {
    return XLSX.utils.encode_cell({ r: row1indexed - 1, c: col0indexed });
  }

  const lastMonthCol = 4 + numMonths - 1; // 0-indexed
  const lastMonthColLetter = XLSX.utils.encode_col(lastMonthCol);

  // Find team member rate row (1-indexed in sheet)
  const rateRowMap = {};
  team.forEach((m, i) => {
    rateRowMap[m.name] = teamStartRow + i; // 1-indexed
  });

  // Walk through wsData to find task rows, section subtotal rows, expense rows, grand total
  let currentSheetRow = 1;
  const sectionSubtotalRows = [];
  const expenseAmountRows = [];
  const taskDataRows = []; // {row1, memberName} for per-person summary

  // Re-walk to annotate
  let sectionTaskStart = null;
  let inExpenses = false;
  let expStartRow = null;

  wsData.forEach((rowArr, idx) => {
    const sheetRow = idx + 1;
    const col0 = rowArr[0];
    const col1 = rowArr[1];

    // Detect section header (single non-empty col A, no col B, no col C with number)
    const isSectionHeader =
      typeof col0 === "string" &&
      col0 !== "" &&
      (col1 === "" || col1 === undefined || col1 === null) &&
      (rowArr[2] === null || rowArr[2] === undefined || rowArr[2] === "") &&
      rowArr[3] === null &&
      sheetRow > wbsHeaderRow;

    // Detect task row: col B = member name
    const isTaskRow =
      col1 &&
      typeof col1 === "string" &&
      team.some((m) => m.name === col1) &&
      sheetRow > wbsHeaderRow;

    // Detect subtotal row
    const isSubtotal =
      typeof col0 === "string" && col0.startsWith("Subtotal —");

    if (col0 === "Expenses & Pass-Through Costs") {
      inExpenses = true;
      expStartRow = sheetRow + 1;
    }

    if (isTaskRow && !inExpenses) {
      if (sectionTaskStart === null) sectionTaskStart = sheetRow;

      const rateRow = rateRowMap[col1];
      const eCol = XLSX.utils.encode_col(lastMonthCol);
      const eAddr = cellAddr(sheetRow, COL_E);
      const eEndAddr = `${eCol}${sheetRow}`;
      const dAddr = cellAddr(sheetRow, COL_D);
      const cAddr = cellAddr(sheetRow, COL_C);
      const rateAddr = `$C$${rateRow}`;

      // D = SUM(E..last)
      ws[dAddr] = { t: "n", f: `SUM(E${sheetRow}:${lastMonthColLetter}${sheetRow})` };
      // C = rate * D
      ws[cAddr] = { t: "n", f: `${rateAddr}*D${sheetRow}` };

      taskDataRows.push({ row: sheetRow, memberName: col1 });
    }

    if (isSubtotal && !inExpenses) {
      const end = sheetRow - 1;
      const start = sectionTaskStart;
      sectionTaskStart = null;

      const dAddr = cellAddr(sheetRow, COL_D);
      const cAddr = cellAddr(sheetRow, COL_C);
      ws[cAddr] = { t: "n", f: `SUM(C${start}:C${end})` };
      ws[dAddr] = { t: "n", f: `SUM(D${start}:D${end})` };
      for (let mc = 0; mc < numMonths; mc++) {
        const colLetter = XLSX.utils.encode_col(COL_E + mc);
        const addr = cellAddr(sheetRow, COL_E + mc);
        ws[addr] = { t: "n", f: `SUM(${colLetter}${start}:${colLetter}${end})` };
      }
      sectionSubtotalRows.push(sheetRow);
    }

    if (isSubtotal && inExpenses) {
      const end = sheetRow - 1;
      const cAddr = cellAddr(sheetRow, COL_C);
      ws[cAddr] = { t: "n", f: `SUM(C${expStartRow}:C${end})` };
      expenseAmountRows.push(...Array.from({ length: end - expStartRow + 1 }, (_, i) => expStartRow + i));
      sectionSubtotalRows.push(sheetRow);
      inExpenses = false;
    }

    if (col0 === "TOTAL PROJECT COST") {
      const costParts = sectionSubtotalRows.map((r) => `C${r}`).join(",");
      const hoursParts = taskDataRows.map((t) => `D${t.row}`).join(",");
      ws[cellAddr(sheetRow, COL_C)] = { t: "n", f: `SUM(${costParts})` };
      ws[cellAddr(sheetRow, COL_D)] = { t: "n", f: `SUM(${hoursParts})` };
      for (let mc = 0; mc < numMonths; mc++) {
        const colLetter = XLSX.utils.encode_col(COL_E + mc);
        ws[cellAddr(sheetRow, COL_E + mc)] = {
          t: "n",
          f: `SUM(${sectionSubtotalRows.map((r) => `${colLetter}${r}`).join(",")})`,
        };
      }
    }

    // Per-person summary rows
    if (
      col0 &&
      team.some((m) => m.name === col0) &&
      sheetRow > wsData.findIndex((r) => r[0] === "TOTAL PROJECT COST") + 3
    ) {
      const mName = col0;
      const mTaskRows = taskDataRows.filter((t) => t.memberName === mName);
      if (mTaskRows.length) {
        const cAddr = cellAddr(sheetRow, COL_C);
        const dAddr = cellAddr(sheetRow, COL_D);
        ws[cAddr] = { t: "n", f: `SUM(${mTaskRows.map((t) => `C${t.row}`).join(",")})` };
        ws[dAddr] = { t: "n", f: `SUM(${mTaskRows.map((t) => `D${t.row}`).join(",")})` };
      }
    }
  });

  // ── Column widths ──────────────────────────────────────────────────────────
  ws["!cols"] = [
    { wch: 38 }, // A
    { wch: 16 }, // B
    { wch: 14 }, // C
    { wch: 12 }, // D
    ...Array(numMonths).fill({ wch: 10 }),
  ];

  // ── Freeze panes ───────────────────────────────────────────────────────────
  ws["!freeze"] = { xSplit: 0, ySplit: wbsHeaderRow };

  XLSX.utils.book_append_sheet(wb, ws, "Work Plan");

  const wbOut = XLSX.write(wb, { bookType: "xlsx", type: "array" });
  const blob = new Blob([wbOut], {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  });

  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  const safeName = (clientName || "Client").replace(/[^a-z0-9]/gi, "_");
  a.href = url;
  a.download = `ALA_${safeName}_Strategic_Plan_Workplan.xlsx`;
  a.click();
  URL.revokeObjectURL(url);
}

// ─── COMPONENTS ───────────────────────────────────────────────────────────────

function Input({ label, value, onChange, type = "text", placeholder, small }) {
  return (
    <div style={{ marginBottom: small ? 6 : 12 }}>
      {label && (
        <label style={{ display: "block", fontSize: 11, fontWeight: 700, color: "#4a5568", marginBottom: 3, textTransform: "uppercase", letterSpacing: "0.05em" }}>
          {label}
        </label>
      )}
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        style={{
          width: "100%",
          padding: small ? "5px 8px" : "8px 10px",
          border: "1px solid #cbd5e0",
          borderRadius: 6,
          fontSize: small ? 12 : 13,
          outline: "none",
          boxSizing: "border-box",
          background: "#fff",
          fontFamily: "inherit",
        }}
      />
    </div>
  );
}

function SectionBlock({ section, team, numMonths, monthLabels, onUpdate, onDelete }) {
  const addTask = () => {
    onUpdate({
      ...section,
      tasks: [...section.tasks, { id: Date.now(), label: "New Task" }],
    });
  };

  const updateTask = (taskId, updates) => {
    onUpdate({
      ...section,
      tasks: section.tasks.map((t) => (t.id === taskId ? { ...t, ...updates } : t)),
    });
  };

  const deleteTask = (taskId) => {
    onUpdate({ ...section, tasks: section.tasks.filter((t) => t.id !== taskId) });
  };

  const updateHours = (taskId, memberName, monthIdx, val) => {
    const task = section.tasks.find((t) => t.id === taskId);
    const existing = task?.hours?.[memberName] || Array(numMonths).fill(null);
    const updated = [...existing];
    while (updated.length < numMonths) updated.push(null);
    updated[monthIdx] = val === "" ? null : parseFloat(val) || null;
    updateTask(taskId, {
      hours: { ...(task?.hours || {}), [memberName]: updated },
    });
  };

  const [collapsed, setCollapsed] = useState(false);

  return (
    <div style={{ border: "1px solid #e2e8f0", borderRadius: 8, marginBottom: 16, overflow: "hidden" }}>
      {/* Section header */}
      <div style={{ background: "#1F3864", padding: "10px 14px", display: "flex", alignItems: "center", gap: 8 }}>
        <button
          onClick={() => setCollapsed(!collapsed)}
          style={{ background: "none", border: "none", color: "#fff", cursor: "pointer", fontSize: 14, padding: 0, lineHeight: 1 }}
        >
          {collapsed ? "▶" : "▼"}
        </button>
        <input
          value={section.label}
          onChange={(e) => onUpdate({ ...section, label: e.target.value })}
          style={{ flex: 1, background: "transparent", border: "none", outline: "none", color: "#fff", fontWeight: 700, fontSize: 13, fontFamily: "inherit" }}
        />
        <button
          onClick={onDelete}
          style={{ background: "none", border: "none", color: "#a0aec0", cursor: "pointer", fontSize: 16, padding: 0 }}
          title="Delete section"
        >
          ×
        </button>
      </div>

      {!collapsed && (
        <div style={{ padding: "12px 14px" }}>
          {section.tasks.map((task) => (
            <TaskBlock
              key={task.id}
              task={task}
              team={team}
              numMonths={numMonths}
              monthLabels={monthLabels}
              onUpdate={(updates) => updateTask(task.id, updates)}
              onDelete={() => deleteTask(task.id)}
              onHoursChange={(memberName, monthIdx, val) =>
                updateHours(task.id, memberName, monthIdx, val)
              }
            />
          ))}
          <button
            onClick={addTask}
            style={{ fontSize: 12, color: "#2E75B6", background: "none", border: "1px dashed #2E75B6", borderRadius: 6, padding: "5px 12px", cursor: "pointer", marginTop: 4 }}
          >
            + Add Task
          </button>
        </div>
      )}
    </div>
  );
}

function TaskBlock({ task, team, numMonths, monthLabels, onUpdate, onDelete, onHoursChange }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div style={{ background: "#f7fafc", border: "1px solid #e2e8f0", borderRadius: 6, marginBottom: 8, overflow: "hidden" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "7px 10px", background: "#EDF2F7" }}>
        <button
          onClick={() => setExpanded(!expanded)}
          style={{ background: "none", border: "none", color: "#4a5568", cursor: "pointer", fontSize: 12, padding: 0 }}
        >
          {expanded ? "▼" : "▶"}
        </button>
        <input
          value={task.label}
          onChange={(e) => onUpdate({ label: e.target.value })}
          style={{ flex: 1, background: "transparent", border: "none", outline: "none", fontSize: 12, fontFamily: "inherit", color: "#2d3748", fontWeight: 600 }}
        />
        <button
          onClick={onDelete}
          style={{ background: "none", border: "none", color: "#a0aec0", cursor: "pointer", fontSize: 14, padding: 0 }}
        >
          ×
        </button>
      </div>

      {expanded && team.length > 0 && (
        <div style={{ padding: "8px 10px", overflowX: "auto" }}>
          <table style={{ borderCollapse: "collapse", fontSize: 11, width: "100%" }}>
            <thead>
              <tr>
                <th style={{ textAlign: "left", padding: "3px 6px", color: "#4a5568", fontWeight: 700, minWidth: 100 }}>
                  Team Member
                </th>
                {monthLabels.map((m, i) => (
                  <th key={i} style={{ textAlign: "center", padding: "3px 4px", color: "#4a5568", fontWeight: 700, minWidth: 52 }}>
                    {m.split(" ")[0]}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {team.map((member) => (
                <tr key={member.id}>
                  <td style={{ padding: "3px 6px", color: "#2d3748", fontSize: 11 }}>{member.name}</td>
                  {Array.from({ length: numMonths }, (_, mi) => (
                    <td key={mi} style={{ padding: "2px 3px" }}>
                      <input
                        type="number"
                        min="0"
                        step="0.25"
                        value={task.hours?.[member.name]?.[mi] ?? ""}
                        onChange={(e) => onHoursChange(member.name, mi, e.target.value)}
                        style={{
                          width: 48,
                          textAlign: "center",
                          padding: "3px 4px",
                          border: "1px solid #cbd5e0",
                          borderRadius: 4,
                          fontSize: 11,
                          fontFamily: "inherit",
                          background: "#fff",
                        }}
                        placeholder="0"
                      />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ─── MAIN APP ─────────────────────────────────────────────────────────────────
export default function WorkPlanBuilder() {
  const [step, setStep] = useState(1); // 1=project, 2=team, 3=tasks, 4=expenses

  // Project info
  const [clientName, setClientName] = useState("");
  const [projectTitle, setProjectTitle] = useState("Strategic Plan");
  const [startMonth, setStartMonth] = useState("");
  const [numMonths, setNumMonths] = useState(8);

  // Team
  const [team, setTeam] = useState([
    { id: 1, name: "David S", role: "Lead Advisor", rate: 250 },
  ]);

  // Sections
  const [sections, setSections] = useState(
    DEFAULT_SECTIONS.map((s) => ({
      ...s,
      tasks: s.tasks.map((t) => ({ ...t, hours: {} })),
    }))
  );

  // Expenses
  const [expenses, setExpenses] = useState([
    { id: 1, label: "Travel (Retreat — Flights, Hotel, Incidentals)", amount: 0 },
    { id: 2, label: "Survey Software", amount: 0 },
  ]);

  const monthLabels = getMonthLabels(startMonth, numMonths);

  const addTeamMember = () => {
    setTeam([...team, { id: Date.now(), name: "", role: "", rate: 0 }]);
  };
  const updateMember = (id, field, val) => {
    setTeam(team.map((m) => (m.id === id ? { ...m, [field]: val } : m)));
  };
  const deleteMember = (id) => setTeam(team.filter((m) => m.id !== id));

  const addSection = () => {
    setSections([
      ...sections,
      { id: Date.now(), label: "New Section", tasks: [{ id: Date.now() + 1, label: "New Task", hours: {} }] },
    ]);
  };
  const updateSection = (id, updated) => {
    setSections(sections.map((s) => (s.id === id ? updated : s)));
  };
  const deleteSection = (id) => setSections(sections.filter((s) => s.id !== id));

  const addExpense = () => {
    setExpenses([...expenses, { id: Date.now(), label: "", amount: 0 }]);
  };
  const updateExpense = (id, field, val) => {
    setExpenses(expenses.map((e) => (e.id === id ? { ...e, [field]: val } : e)));
  };
  const deleteExpense = (id) => setExpenses(expenses.filter((e) => e.id !== id));

  const handleDownload = () => {
    generateXLSX({
      clientName,
      projectTitle,
      team,
      startMonth,
      numMonths,
      sections,
      expenses: expenses.filter((e) => e.label && e.amount > 0),
    });
  };

  const stepValid = {
    1: clientName.trim() !== "" && numMonths > 0,
    2: team.length > 0 && team.every((m) => m.name.trim() !== "" && m.rate > 0),
    3: sections.length > 0,
    4: true,
  };

  const ACCENT = "#1F3864";
  const BLUE = "#2E75B6";

  return (
    <div style={{ fontFamily: "'Georgia', serif", maxWidth: 900, margin: "0 auto", padding: "24px 20px", background: "#f8f9fa", minHeight: "100vh" }}>
      {/* Header */}
      <div style={{ background: ACCENT, borderRadius: 10, padding: "18px 24px", marginBottom: 24, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div>
          <div style={{ color: "#a0c4ff", fontSize: 10, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", fontFamily: "Arial, sans-serif" }}>
            Amplify Leadership Advisors
          </div>
          <div style={{ color: "#fff", fontSize: 20, fontWeight: 700, marginTop: 2 }}>
            Work Plan Builder
          </div>
        </div>
        <div style={{ color: "#a0c4ff", fontSize: 12, fontFamily: "Arial, sans-serif" }}>
          Strategic Plan
        </div>
      </div>

      {/* Steps */}
      <div style={{ display: "flex", gap: 6, marginBottom: 24 }}>
        {[
          { n: 1, label: "Project Info" },
          { n: 2, label: "Team" },
          { n: 3, label: "Work Plan" },
          { n: 4, label: "Expenses" },
        ].map(({ n, label }) => (
          <button
            key={n}
            onClick={() => setStep(n)}
            style={{
              flex: 1,
              padding: "9px 6px",
              borderRadius: 7,
              border: step === n ? `2px solid ${BLUE}` : "2px solid #e2e8f0",
              background: step === n ? BLUE : "#fff",
              color: step === n ? "#fff" : "#4a5568",
              fontWeight: 700,
              fontSize: 12,
              cursor: "pointer",
              fontFamily: "Arial, sans-serif",
              transition: "all 0.15s",
            }}
          >
            <span style={{ opacity: 0.7, fontSize: 10 }}>{n}.</span> {label}
          </button>
        ))}
      </div>

      {/* Step 1: Project Info */}
      {step === 1 && (
        <div style={{ background: "#fff", borderRadius: 10, padding: 24, boxShadow: "0 1px 4px rgba(0,0,0,0.08)" }}>
          <h2 style={{ margin: "0 0 18px", fontSize: 16, color: ACCENT }}>Project Information</h2>
          <Input label="Client / Organization Name" value={clientName} onChange={setClientName} placeholder="e.g. Center Theatre Group" />
          <Input label="Project Title" value={projectTitle} onChange={setProjectTitle} placeholder="e.g. Strategic Plan" />
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            <Input label="Start Month" value={startMonth} onChange={setStartMonth} type="month" />
            <div>
              <label style={{ display: "block", fontSize: 11, fontWeight: 700, color: "#4a5568", marginBottom: 3, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                Number of Months
              </label>
              <input
                type="number"
                min={1}
                max={24}
                value={numMonths}
                onChange={(e) => setNumMonths(Math.max(1, parseInt(e.target.value) || 1))}
                style={{ width: "100%", padding: "8px 10px", border: "1px solid #cbd5e0", borderRadius: 6, fontSize: 13, fontFamily: "inherit", boxSizing: "border-box" }}
              />
            </div>
          </div>
          {startMonth && (
            <div style={{ marginTop: 12, padding: "8px 12px", background: "#EDF2F7", borderRadius: 6, fontSize: 12, color: "#4a5568", fontFamily: "Arial, sans-serif" }}>
              Months: {monthLabels.join(" · ")}
            </div>
          )}
          <div style={{ textAlign: "right", marginTop: 20 }}>
            <button
              disabled={!stepValid[1]}
              onClick={() => setStep(2)}
              style={{ background: stepValid[1] ? BLUE : "#a0aec0", color: "#fff", border: "none", borderRadius: 7, padding: "9px 24px", fontWeight: 700, fontSize: 13, cursor: stepValid[1] ? "pointer" : "default", fontFamily: "Arial, sans-serif" }}
            >
              Next: Team →
            </button>
          </div>
        </div>
      )}

      {/* Step 2: Team */}
      {step === 2 && (
        <div style={{ background: "#fff", borderRadius: 10, padding: 24, boxShadow: "0 1px 4px rgba(0,0,0,0.08)" }}>
          <h2 style={{ margin: "0 0 18px", fontSize: 16, color: ACCENT }}>Team Members & Rates</h2>
          {team.map((m, i) => (
            <div key={m.id} style={{ display: "grid", gridTemplateColumns: "2fr 1.5fr 1fr auto", gap: 10, marginBottom: 10, alignItems: "end" }}>
              <Input small label={i === 0 ? "Name" : undefined} value={m.name} onChange={(v) => updateMember(m.id, "name", v)} placeholder="e.g. Sami C" />
              <Input small label={i === 0 ? "Role" : undefined} value={m.role} onChange={(v) => updateMember(m.id, "role", v)} placeholder="e.g. Project Manager" />
              <Input small label={i === 0 ? "Rate ($/hr)" : undefined} value={m.rate} onChange={(v) => updateMember(m.id, "rate", parseFloat(v) || 0)} type="number" />
              <button
                onClick={() => deleteMember(m.id)}
                style={{ background: "none", border: "1px solid #fed7d7", borderRadius: 6, color: "#e53e3e", cursor: "pointer", padding: "5px 10px", fontSize: 14, marginBottom: 12 }}
              >
                ×
              </button>
            </div>
          ))}
          <button
            onClick={addTeamMember}
            style={{ fontSize: 12, color: BLUE, background: "none", border: `1px dashed ${BLUE}`, borderRadius: 6, padding: "6px 14px", cursor: "pointer", marginBottom: 8, fontFamily: "Arial, sans-serif" }}
          >
            + Add Team Member
          </button>
          <div style={{ display: "flex", justifyContent: "space-between", marginTop: 16 }}>
            <button onClick={() => setStep(1)} style={{ background: "#fff", color: "#4a5568", border: "1px solid #e2e8f0", borderRadius: 7, padding: "9px 18px", fontWeight: 600, fontSize: 13, cursor: "pointer", fontFamily: "Arial, sans-serif" }}>
              ← Back
            </button>
            <button
              disabled={!stepValid[2]}
              onClick={() => setStep(3)}
              style={{ background: stepValid[2] ? BLUE : "#a0aec0", color: "#fff", border: "none", borderRadius: 7, padding: "9px 24px", fontWeight: 700, fontSize: 13, cursor: stepValid[2] ? "pointer" : "default", fontFamily: "Arial, sans-serif" }}
            >
              Next: Work Plan →
            </button>
          </div>
        </div>
      )}

      {/* Step 3: Work Plan */}
      {step === 3 && (
        <div>
          <div style={{ background: "#fff", borderRadius: 10, padding: "14px 20px", marginBottom: 16, boxShadow: "0 1px 4px rgba(0,0,0,0.08)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div style={{ fontSize: 13, color: "#4a5568", fontFamily: "Arial, sans-serif" }}>
              <strong>Click ▶ on a task to enter hours by team member and month.</strong> Sections and tasks are pre-loaded from ALA's standard strategic plan template.
            </div>
          </div>
          {sections.map((section) => (
            <SectionBlock
              key={section.id}
              section={section}
              team={team}
              numMonths={numMonths}
              monthLabels={monthLabels}
              onUpdate={(updated) => updateSection(section.id, updated)}
              onDelete={() => deleteSection(section.id)}
            />
          ))}
          <button
            onClick={addSection}
            style={{ fontSize: 12, color: BLUE, background: "none", border: `1px dashed ${BLUE}`, borderRadius: 6, padding: "7px 16px", cursor: "pointer", marginBottom: 16, fontFamily: "Arial, sans-serif" }}
          >
            + Add Section
          </button>
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <button onClick={() => setStep(2)} style={{ background: "#fff", color: "#4a5568", border: "1px solid #e2e8f0", borderRadius: 7, padding: "9px 18px", fontWeight: 600, fontSize: 13, cursor: "pointer", fontFamily: "Arial, sans-serif" }}>
              ← Back
            </button>
            <button
              onClick={() => setStep(4)}
              style={{ background: BLUE, color: "#fff", border: "none", borderRadius: 7, padding: "9px 24px", fontWeight: 700, fontSize: 13, cursor: "pointer", fontFamily: "Arial, sans-serif" }}
            >
              Next: Expenses →
            </button>
          </div>
        </div>
      )}

      {/* Step 4: Expenses + Download */}
      {step === 4 && (
        <div style={{ background: "#fff", borderRadius: 10, padding: 24, boxShadow: "0 1px 4px rgba(0,0,0,0.08)" }}>
          <h2 style={{ margin: "0 0 18px", fontSize: 16, color: ACCENT }}>Expenses & Pass-Through Costs</h2>
          <p style={{ fontSize: 12, color: "#718096", marginBottom: 16, fontFamily: "Arial, sans-serif" }}>
            These are pass-through costs (travel, software, stipends, etc.) added to the total project cost. Leave amount at 0 to omit.
          </p>
          {expenses.map((exp, i) => (
            <div key={exp.id} style={{ display: "grid", gridTemplateColumns: "3fr 1fr auto", gap: 10, marginBottom: 8, alignItems: "end" }}>
              <Input small label={i === 0 ? "Expense Description" : undefined} value={exp.label} onChange={(v) => updateExpense(exp.id, "label", v)} placeholder="e.g. Travel — Retreat" />
              <Input small label={i === 0 ? "Amount ($)" : undefined} value={exp.amount} onChange={(v) => updateExpense(exp.id, "amount", parseFloat(v) || 0)} type="number" />
              <button
                onClick={() => deleteExpense(exp.id)}
                style={{ background: "none", border: "1px solid #fed7d7", borderRadius: 6, color: "#e53e3e", cursor: "pointer", padding: "5px 10px", fontSize: 14, marginBottom: 12 }}
              >
                ×
              </button>
            </div>
          ))}
          <button
            onClick={addExpense}
            style={{ fontSize: 12, color: BLUE, background: "none", border: `1px dashed ${BLUE}`, borderRadius: 6, padding: "6px 14px", cursor: "pointer", marginBottom: 24, fontFamily: "Arial, sans-serif" }}
          >
            + Add Expense
          </button>

          {/* Summary */}
          <div style={{ background: "#EDF2F7", borderRadius: 8, padding: "14px 18px", marginBottom: 24, fontFamily: "Arial, sans-serif" }}>
            <div style={{ fontWeight: 700, fontSize: 13, color: ACCENT, marginBottom: 10 }}>Summary</div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6, fontSize: 12, color: "#4a5568" }}>
              <span>Client:</span><strong>{clientName || "—"}</strong>
              <span>Project:</span><strong>{projectTitle}</strong>
              <span>Timeline:</span><strong>{numMonths} months{startMonth ? ` starting ${monthLabels[0]}` : ""}</strong>
              <span>Team members:</span><strong>{team.length}</strong>
              <span>Sections:</span><strong>{sections.length}</strong>
              <span>Total tasks:</span><strong>{sections.reduce((a, s) => a + s.tasks.length, 0)}</strong>
            </div>
          </div>

          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <button onClick={() => setStep(3)} style={{ background: "#fff", color: "#4a5568", border: "1px solid #e2e8f0", borderRadius: 7, padding: "9px 18px", fontWeight: 600, fontSize: 13, cursor: "pointer", fontFamily: "Arial, sans-serif" }}>
              ← Back
            </button>
            <button
              onClick={handleDownload}
              style={{ background: ACCENT, color: "#fff", border: "none", borderRadius: 8, padding: "12px 28px", fontWeight: 700, fontSize: 14, cursor: "pointer", fontFamily: "Arial, sans-serif", boxShadow: "0 2px 8px rgba(31,56,100,0.3)", display: "flex", alignItems: "center", gap: 8 }}
            >
              ⬇ Download Work Plan (.xlsx)
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
