import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import Sidebar from "../components/Sidebar";
import { useAuth } from "../AuthContext";
import "./Audit.css";

const VERIFICATION_OPTIONS = ["Unverified", "Verified", "Missing", "Damaged"];

function formatRange(start, end) {
  if (!start && !end) return "";
  const s = start ? new Date(start) : null;
  const e = end ? new Date(end) : null;
  const fmt = (d) => d.toLocaleDateString(undefined, { day: "numeric", month: "short" });
  if (s && e) return `${fmt(s)} – ${fmt(e)}`;
  return fmt(s || e);
}

export default function Audit() {
  const { user } = useAuth();
  const canManage = user && ["AssetManager", "Admin"].includes(user.role);
  const [cycles, setCycles] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [cycle, setCycle] = useState(null);
  const [departments, setDepartments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showNewModal, setShowNewModal] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [closing, setClosing] = useState(false);
  const [discrepancyNotice, setDiscrepancyNotice] = useState(null);

  const loadCycles = useCallback(() => {
    setError("");
    api
      .auditCycles()
      .then((list) => {
        setCycles(list);
        if (!selectedId && list.length) setSelectedId(list[0].id);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    loadCycles();
    api.departments().then(setDepartments).catch(() => {});
  }, [loadCycles]);

  const loadCycle = useCallback((id) => {
    if (!id) return;
    api.auditCycle(id).then(setCycle).catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    loadCycle(selectedId);
  }, [selectedId, loadCycle]);

  async function handleCreate(form) {
    setSubmitting(true);
    setError("");
    try {
      const created = await api.createAuditCycle(form);
      setShowNewModal(false);
      setCycles((prev) => [created, ...prev]);
      setSelectedId(created.id);
      setCycle(created);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleVerify(itemId, verification) {
    setError("");
    try {
      await api.updateAuditItem(itemId, { verification });
      loadCycle(selectedId);
      setCycles((prev) =>
        prev.map((c) => (c.id === selectedId ? { ...c } : c))
      );
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleClose() {
    if (!cycle) return;
    setClosing(true);
    setError("");
    try {
      const result = await api.closeAuditCycle(cycle.id);
      setDiscrepancyNotice(result.discrepancy_report);
      loadCycle(selectedId);
      loadCycles();
    } catch (err) {
      setError(err.message);
    } finally {
      setClosing(false);
    }
  }

  const flaggedCount = cycle
    ? (cycle.items || []).filter((i) => ["Missing", "Damaged"].includes(i.verification)).length
    : 0;

  return (
    <div className="shell">
      <Sidebar active="Audit" />
      <main className="content">
        <header className="content-header">
          <h1>Asset Audit</h1>
          {canManage && (
            <button className="btn-primary" onClick={() => setShowNewModal(true)}>
              + New audit cycle
            </button>
          )}
        </header>

        {error && <div className="banner banner-error">{error}</div>}

        {loading ? (
          <p className="empty-state">Loading…</p>
        ) : cycles.length === 0 ? (
          <p className="empty-state">
            No audit cycles yet. Start one to run a structured verification pass.
          </p>
        ) : (
          <>
            <div className="cycle-picker">
              {cycles.map((c) => (
                <button
                  key={c.id}
                  className={"cycle-chip" + (c.id === selectedId ? " active" : "")}
                  onClick={() => setSelectedId(c.id)}
                >
                  {c.title}
                  <span className={"cycle-chip-status status-" + c.status.toLowerCase()}>
                    {c.status}
                  </span>
                </button>
              ))}
            </div>

            {cycle && (
              <>
                <div className="audit-summary">
                  <div className="audit-summary-title">
                    {cycle.title}
                    {cycle.department_name ? ` — ${cycle.department_name} dept` : ""}
                    {formatRange(cycle.start_date, cycle.end_date)
                      ? ` — ${formatRange(cycle.start_date, cycle.end_date)}`
                      : ""}
                  </div>
                  {cycle.auditor_names && (
                    <div className="audit-summary-auditors">
                      Auditors: {cycle.auditor_names}
                    </div>
                  )}
                </div>

                <table className="audit-table">
                  <thead>
                    <tr>
                      <th>Asset</th>
                      <th>Expected location</th>
                      <th>Verification</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(cycle.items || []).map((item) => (
                      <tr key={item.id}>
                        <td>
                          <span className="asset-tag">{item.asset_tag}</span>{" "}
                          {item.asset_name}
                        </td>
                        <td className="muted">{item.expected_location || "—"}</td>
                        <td>
                          {cycle.status === "Closed" ? (
                            <span className={"pill pill-" + item.verification.toLowerCase()}>
                              {item.verification}
                            </span>
                          ) : (
                            <select
                              className={"pill-select pill-" + item.verification.toLowerCase()}
                              value={item.verification}
                              onChange={(e) => handleVerify(item.id, e.target.value)}
                            >
                              {VERIFICATION_OPTIONS.map((v) => (
                                <option key={v} value={v}>
                                  {v}
                                </option>
                              ))}
                            </select>
                          )}
                        </td>
                      </tr>
                    ))}
                    {(cycle.items || []).length === 0 && (
                      <tr>
                        <td colSpan={3} className="empty-state">
                          No assets in scope for this cycle.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>

                {(flaggedCount > 0 || discrepancyNotice) && (
                  <div className="banner banner-flagged">
                    {flaggedCount} asset{flaggedCount === 1 ? "" : "s"} flagged - discrepancy
                    report generated automatically
                  </div>
                )}

                <button
                  className="btn-primary"
                  onClick={handleClose}
                  disabled={cycle.status === "Closed" || closing || !canManage}
                  title={!canManage ? "Only an Asset Manager or Admin can close a cycle" : undefined}
                >
                  {cycle.status === "Closed"
                    ? "Audit cycle closed"
                    : closing
                    ? "Closing…"
                    : "Close audit cycle"}
                </button>
              </>
            )}
          </>
        )}
      </main>

      {showNewModal && (
        <NewCycleModal
          departments={departments}
          submitting={submitting}
          onCancel={() => setShowNewModal(false)}
          onSave={handleCreate}
        />
      )}
    </div>
  );
}

function NewCycleModal({ departments, submitting, onCancel, onSave }) {
  const [form, setForm] = useState({
    title: "",
    department_id: "",
    start_date: "",
    end_date: "",
    auditor_names: "",
  });

  function update(field) {
    return (e) => setForm((f) => ({ ...f, [field]: e.target.value }));
  }

  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <h2>New audit cycle</h2>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            onSave({ ...form, department_id: form.department_id || null });
          }}
        >
          <label className="modal-field">
            <span>Title</span>
            <input
              type="text"
              value={form.title}
              onChange={update("title")}
              placeholder="Q3 audit: Engineering dept"
              required
            />
          </label>

          <label className="modal-field">
            <span>Department (scope)</span>
            <select value={form.department_id} onChange={update("department_id")}>
              <option value="">All departments</option>
              {departments.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </select>
          </label>

          <div className="modal-row">
            <label className="modal-field">
              <span>Start date</span>
              <input type="date" value={form.start_date} onChange={update("start_date")} />
            </label>
            <label className="modal-field">
              <span>End date</span>
              <input type="date" value={form.end_date} onChange={update("end_date")} />
            </label>
          </div>

          <label className="modal-field">
            <span>Auditors</span>
            <input
              type="text"
              value={form.auditor_names}
              onChange={update("auditor_names")}
              placeholder="A. Rao, S. Iqbal"
            />
          </label>

          <div className="modal-actions">
            <button type="button" className="btn-secondary" onClick={onCancel}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={submitting}>
              {submitting ? "Creating…" : "Start audit cycle"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
