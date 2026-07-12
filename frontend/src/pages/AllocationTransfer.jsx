import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import Sidebar from "../components/Sidebar";
import "./AllocationTransfer.css";

export default function AllocationTransfer() {
  const [assets, setAssets] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [selectedAssetId, setSelectedAssetId] = useState("");

  const [allocation, setAllocation] = useState(null); // { allocated, employee_name, department_name, ... }
  const [history, setHistory] = useState([]);

  const [toEmployeeId, setToEmployeeId] = useState("");
  const [reason, setReason] = useState("");

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    Promise.all([api.assets({ per_page: 100 }), api.employees().catch(() => [])])
      .then(([assetRes, employeeList]) => {
        setAssets(assetRes.items || []);
        setEmployees(employeeList || []);
        if (assetRes.items?.length) setSelectedAssetId(assetRes.items[0].id);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const loadAssetDetail = useCallback((assetId) => {
    if (!assetId) return;
    setError("");
    setNotice("");
    Promise.all([api.assetAllocation(assetId), api.assetAllocationHistory(assetId)])
      .then(([alloc, hist]) => {
        setAllocation(alloc);
        setHistory(hist);
      })
      .catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    if (selectedAssetId) loadAssetDetail(selectedAssetId);
  }, [selectedAssetId, loadAssetDetail]);

  const selectedAsset = assets.find((a) => a.id === selectedAssetId);

  async function handleSubmitTransfer(e) {
    e.preventDefault();
    setError("");
    setNotice("");

    if (!toEmployeeId) {
      setError("Select an employee to transfer this asset to.");
      return;
    }
    if (!reason.trim()) {
      setError("A reason is required for the transfer request.");
      return;
    }

    setSubmitting(true);
    try {
      await api.createTransferRequest({
        asset_id: selectedAssetId,
        to_employee_id: toEmployeeId,
        reason,
      });
      setNotice("Transfer request submitted for approval.");
      setToEmployeeId("");
      setReason("");
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="shell">
      <Sidebar active="Allocation & Transfer" />
      <main className="content">
        <header className="content-header">
          <h1>Allocation &amp; Transfer</h1>
        </header>

        {loading ? (
          <p className="empty-state">Loading…</p>
        ) : (
          <div className="alloc-panel">
            <label className="alloc-field">
              <span>Asset</span>
              <select
                value={selectedAssetId}
                onChange={(e) => setSelectedAssetId(e.target.value)}
              >
                {assets.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.asset_tag} - {a.name}
                  </option>
                ))}
              </select>
            </label>

            {allocation?.allocated && (
              <div className="alloc-block">
                <div className="alloc-block-line">
                  Already Allocated to {allocation.employee_name}
                  {allocation.department_name ? ` (${allocation.department_name})` : ""}
                </div>
                <div className="alloc-block-line alloc-block-sub">
                  Direct re-allocation is blocked - submit a transfer request below
                </div>
              </div>
            )}

            {allocation && !allocation.allocated && (
              <div className="alloc-free">
                This asset is not currently allocated - it can be assigned directly from the
                Assets screen.
              </div>
            )}

            {notice && <div className="banner banner-success">{notice}</div>}
            {error && <div className="banner banner-error">{error}</div>}

            <h2 className="alloc-section-title">Transfer Request</h2>

            <form onSubmit={handleSubmitTransfer} className="transfer-form">
              <div className="transfer-row">
                <label className="alloc-field">
                  <span>From</span>
                  <input
                    type="text"
                    value={allocation?.allocated ? allocation.employee_name : "Unassigned"}
                    disabled
                  />
                </label>

                <label className="alloc-field">
                  <span>To</span>
                  <select value={toEmployeeId} onChange={(e) => setToEmployeeId(e.target.value)}>
                    <option value="">Select Employee….</option>
                    {employees
                      .filter((e) => e.id !== allocation?.employee_id)
                      .map((e) => (
                        <option key={e.id} value={e.id}>
                          {e.name}
                        </option>
                      ))}
                  </select>
                </label>
              </div>

              <label className="alloc-field">
                <span>Reason</span>
                <textarea
                  rows={5}
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  placeholder="Why is this asset being transferred?"
                />
              </label>

              <button type="submit" className="btn-primary" disabled={submitting}>
                {submitting ? "Submitting…" : "Submit Request"}
              </button>
            </form>

            <h2 className="alloc-section-title alloc-history-title">Allocation history</h2>
            <div className="alloc-history">
              {history.length === 0 && (
                <p className="empty-state">No allocation history for this asset yet.</p>
              )}
              {history.map((h, idx) => (
                <div className="alloc-history-row" key={idx}>
                  <span className="alloc-history-date">
                    {h.date
                      ? new Date(h.date).toLocaleDateString(undefined, {
                          month: "short",
                          day: "2-digit",
                        })
                      : "--"}
                  </span>
                  <span className="alloc-history-desc">{h.description}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {!loading && !selectedAsset && assets.length === 0 && (
          <p className="empty-state">No assets registered yet — add one from the Assets screen.</p>
        )}
      </main>
    </div>
  );
}