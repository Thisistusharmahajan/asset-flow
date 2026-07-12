import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import Sidebar from "../components/Sidebar";
import { useAuth } from "../AuthContext";
import "./Maintenance.css";

const COLUMNS = ["Pending", "Approved", "Technician Assigned", "In Progress", "Resolved"];

// The forward move available from each column, and what it needs from the user.
const NEXT_STEP = {
  "Pending": { next: "Approved", label: "Approve", needs: null },
  "Approved": { next: "Technician Assigned", label: "Assign technician", needs: "technician" },
  "Technician Assigned": { next: "In Progress", label: "Start work", needs: null },
  "In Progress": { next: "Resolved", label: "Mark resolved", needs: "notes" },
  "Resolved": null,
};

export default function Maintenance() {
  const { user } = useAuth();
  const canManage = user && ["AssetManager", "Admin"].includes(user.role);
  const [tickets, setTickets] = useState([]);
  const [assets, setAssets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showRaiseModal, setShowRaiseModal] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [actionModal, setActionModal] = useState(null); // { ticket, needs }

  const load = useCallback(() => {
    setError("");
    api
      .maintenanceRequests()
      .then(setTickets)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
    api.assets({ per_page: 100 }).then((res) => {
      setAssets(Array.isArray(res) ? res : res.items || []);
    }).catch(() => {});
  }, [load]);

  async function handleRaise(form) {
    setSubmitting(true);
    setError("");
    try {
      await api.createMaintenanceRequest(form);
      setShowRaiseModal(false);
      load();
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  async function advance(ticket, extra = {}) {
    const step = NEXT_STEP[ticket.status];
    if (!step) return;
    setError("");
    try {
      await api.updateMaintenanceRequest(ticket.id, { status: step.next, ...extra });
      setActionModal(null);
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  function handleCardAction(ticket) {
    const step = NEXT_STEP[ticket.status];
    if (!step) return;
    if (step.needs) {
      setActionModal({ ticket, needs: step.needs, label: step.label });
    } else {
      advance(ticket);
    }
  }

  const byStatus = COLUMNS.reduce((acc, col) => {
    acc[col] = tickets.filter((t) => t.status === col);
    return acc;
  }, {});

  return (
    <div className="shell">
      <Sidebar active="Maintenance" />
      <main className="content">
        <header className="content-header">
          <h1>Maintenance Management</h1>
          <button className="btn-primary" onClick={() => setShowRaiseModal(true)}>
            + Raise request
          </button>
        </header>

        {error && <div className="banner banner-error">{error}</div>}

        {loading ? (
          <p className="empty-state">Loading…</p>
        ) : (
          <div className="kanban">
            {COLUMNS.map((col) => (
              <div className="kanban-col" key={col}>
                <div className="kanban-col-header">{col}</div>
                <div className="kanban-col-body">
                  {byStatus[col].length === 0 && (
                    <p className="kanban-empty">Nothing here</p>
                  )}
                  {byStatus[col].map((t) => {
                    const step = NEXT_STEP[t.status];
                    return (
                      <div
                        className={"kanban-card" + (t.status === "Resolved" ? " resolved" : "")}
                        key={t.id}
                      >
                        <div className="kanban-card-tag">{t.asset_tag}</div>
                        <div className="kanban-card-desc">
                          {t.status === "Resolved" && t.resolved_at
                            ? `${t.issue_description} — resolved ${new Date(
                                t.resolved_at
                              ).toLocaleDateString(undefined, { day: "numeric", month: "short" })}`
                            : t.issue_description}
                        </div>
                        {t.technician_name && (
                          <div className="kanban-card-meta">tech: {t.technician_name}</div>
                        )}
                        {t.notes && t.status !== "Resolved" && (
                          <div className="kanban-card-meta">{t.notes}</div>
                        )}
                        {step && canManage && (
                          <button
                            className="kanban-card-action"
                            onClick={() => handleCardAction(t)}
                          >
                            {step.label}
                          </button>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        )}

        <p className="kanban-footnote">
          Approving a card moves the asset to Under Maintenance, resolving it
          returns the asset to Available.
        </p>
      </main>

      {showRaiseModal && (
        <RaiseRequestModal
          assets={assets}
          submitting={submitting}
          onCancel={() => setShowRaiseModal(false)}
          onSave={handleRaise}
        />
      )}

      {actionModal && (
        <ActionModal
          ticket={actionModal.ticket}
          needs={actionModal.needs}
          label={actionModal.label}
          onCancel={() => setActionModal(null)}
          onSave={(extra) => advance(actionModal.ticket, extra)}
        />
      )}
    </div>
  );
}

function RaiseRequestModal({ assets, submitting, onCancel, onSave }) {
  const [form, setForm] = useState({ asset_id: "", issue_description: "", priority: "Medium" });

  function update(field) {
    return (e) => setForm((f) => ({ ...f, [field]: e.target.value }));
  }

  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <h2>Raise maintenance request</h2>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            onSave(form);
          }}
        >
          <label className="modal-field">
            <span>Asset</span>
            <select value={form.asset_id} onChange={update("asset_id")} required>
              <option value="" disabled>
                Select an asset…
              </option>
              {assets.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.asset_tag} — {a.name}
                </option>
              ))}
            </select>
          </label>

          <label className="modal-field">
            <span>Describe the issue</span>
            <textarea
              value={form.issue_description}
              onChange={update("issue_description")}
              rows={3}
              placeholder="e.g. Projector bulb not turning on"
              required
            />
          </label>

          <label className="modal-field">
            <span>Priority</span>
            <select value={form.priority} onChange={update("priority")}>
              <option>Low</option>
              <option>Medium</option>
              <option>High</option>
              <option>Critical</option>
            </select>
          </label>

          <div className="modal-actions">
            <button type="button" className="btn-secondary" onClick={onCancel}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={submitting}>
              {submitting ? "Submitting…" : "Submit request"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function ActionModal({ ticket, needs, label, onCancel, onSave }) {
  const [value, setValue] = useState("");

  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <h2>{label}</h2>
        <p className="modal-subtitle">
          {ticket.asset_tag} — {ticket.issue_description}
        </p>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            onSave(
              needs === "technician" ? { technician_name: value } : { notes: value }
            );
          }}
        >
          {needs === "technician" ? (
            <label className="modal-field">
              <span>Technician name</span>
              <input
                type="text"
                value={value}
                onChange={(e) => setValue(e.target.value)}
                placeholder="R. Varma"
                required
              />
            </label>
          ) : (
            <label className="modal-field">
              <span>Resolution notes</span>
              <textarea
                value={value}
                onChange={(e) => setValue(e.target.value)}
                rows={2}
                placeholder="e.g. Parts ordered, resolved on-site"
              />
            </label>
          )}

          <div className="modal-actions">
            <button type="button" className="btn-secondary" onClick={onCancel}>
              Cancel
            </button>
            <button type="submit" className="btn-primary">
              Confirm
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
