import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import { useAuth } from "../AuthContext";
import Sidebar from "../components/Sidebar";
import "./Assets.css";

const STATUSES = [
  "Available", "Allocated", "Reserved", "Under Maintenance", "Lost", "Retired", "Disposed",
];

function statusClass(status) {
  return "pill pill-" + status.toLowerCase().replace(/\s+/g, "-");
}

export default function Assets() {
  const { user } = useAuth();
  const canRegister = user?.role === "Admin" || user?.role === "AssetManager";

  const [assets, setAssets] = useState([]);
  const [total, setTotal] = useState(0);
  const [categories, setCategories] = useState([]);
  const [departments, setDepartments] = useState([]);

  const [q, setQ] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [status, setStatus] = useState("");
  const [departmentId, setDepartmentId] = useState("");
  const [page, setPage] = useState(1);
  const perPage = 20;

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showRegister, setShowRegister] = useState(false);
  const [saving, setSaving] = useState(false);

  const loadAssets = useCallback(() => {
    setLoading(true);
    api
      .assets({ q, category_id: categoryId, status, department_id: departmentId, page, per_page: perPage })
      .then((res) => {
        setAssets(res.items);
        setTotal(res.total);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [q, categoryId, status, departmentId, page]);

  useEffect(() => {
    Promise.all([api.categories(), api.departments()])
      .then(([c, d]) => {
        setCategories(c);
        setDepartments(d);
      })
      .catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    const timer = setTimeout(loadAssets, 250);
    return () => clearTimeout(timer);
  }, [loadAssets]);

  async function handleRegister(form) {
    setSaving(true);
    setError("");
    try {
      await api.createAsset(form);
      setShowRegister(false);
      setPage(1);
      loadAssets();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  const totalPages = Math.max(1, Math.ceil(total / perPage));

  return (
    <div className="shell">
      <Sidebar active="Assets" />
      <main className="content">
        <header className="content-header">
          <h1>Assets</h1>
          <span className="content-sub">Asset registrations and directory</span>
        </header>

        {error && <div className="banner banner-error">{error}</div>}

        <div className="assets-search-row">
          <input
            className="assets-search"
            type="text"
            placeholder="Search by tag, name, serial, or QR code.."
            value={q}
            onChange={(e) => {
              setPage(1);
              setQ(e.target.value);
            }}
          />
          {canRegister && (
            <button className="assets-register-btn" onClick={() => setShowRegister(true)}>
              + Register Asset
            </button>
          )}
        </div>

        <div className="assets-filter-row">
          <select
            value={categoryId}
            onChange={(e) => {
              setPage(1);
              setCategoryId(e.target.value);
            }}
          >
            <option value="">Category</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>

          <select
            value={status}
            onChange={(e) => {
              setPage(1);
              setStatus(e.target.value);
            }}
          >
            <option value="">Status</option>
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>

          <select
            value={departmentId}
            onChange={(e) => {
              setPage(1);
              setDepartmentId(e.target.value);
            }}
          >
            <option value="">Department</option>
            {departments.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </select>
        </div>

        <div className="assets-panel">
          <table className="assets-table">
            <thead>
              <tr>
                <th>Tag</th>
                <th>Name</th>
                <th>Category</th>
                <th>Status</th>
                <th>Location</th>
              </tr>
            </thead>
            <tbody>
              {!loading && assets.length === 0 && (
                <tr>
                  <td className="empty-state" colSpan={5}>
                    No assets match these filters.
                  </td>
                </tr>
              )}
              {assets.map((a) => (
                <tr key={a.id}>
                  <td className="assets-cell-tag">{a.asset_tag}</td>
                  <td className="assets-cell-primary">{a.name}</td>
                  <td>{a.category || "--"}</td>
                  <td>
                    <span className={statusClass(a.status)}>{a.status}</span>
                  </td>
                  <td>{a.location || "--"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {loading && <p className="empty-state">Loading…</p>}
        </div>

        {totalPages > 1 && (
          <div className="assets-pagination">
            <button disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
              Previous
            </button>
            <span>
              Page {page} of {totalPages}
            </span>
            <button disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
              Next
            </button>
          </div>
        )}
      </main>

      {showRegister && (
        <RegisterAssetModal
          categories={categories}
          departments={departments}
          saving={saving}
          onCancel={() => setShowRegister(false)}
          onSave={handleRegister}
        />
      )}
    </div>
  );
}

function RegisterAssetModal({ categories, departments, saving, onCancel, onSave }) {
  const [form, setForm] = useState({
    name: "",
    category_id: "",
    department_id: "",
    location: "",
    status: "Available",
    serial_number: "",
    qr_code: "",
    vendor: "",
    condition: "New",
  });

  function update(field) {
    return (e) => setForm((f) => ({ ...f, [field]: e.target.value }));
  }

  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <h2>Register asset</h2>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            onSave(form);
          }}
        >
          <label className="modal-field">
            <span>Asset name</span>
            <input type="text" value={form.name} onChange={update("name")} required placeholder="Dell Laptop" />
          </label>

          <label className="modal-field">
            <span>Category</span>
            <select value={form.category_id} onChange={update("category_id")} required>
              <option value="">Select category</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </label>

          <label className="modal-field">
            <span>Department</span>
            <select value={form.department_id} onChange={update("department_id")}>
              <option value="">--</option>
              {departments.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </select>
          </label>

          <label className="modal-field">
            <span>Location</span>
            <input type="text" value={form.location} onChange={update("location")} placeholder="Bengaluru" />
          </label>

          <label className="modal-field">
            <span>Status</span>
            <select value={form.status} onChange={update("status")}>
              {STATUSES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </label>

          <label className="modal-field">
            <span>Serial number</span>
            <input type="text" value={form.serial_number} onChange={update("serial_number")} />
          </label>

          <label className="modal-field">
            <span>QR code</span>
            <input type="text" value={form.qr_code} onChange={update("qr_code")} />
          </label>

          <label className="modal-field">
            <span>Vendor</span>
            <input type="text" value={form.vendor} onChange={update("vendor")} />
          </label>

          <div className="modal-actions">
            <button type="button" className="btn-secondary" onClick={onCancel}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={saving}>
              {saving ? "Saving…" : "Register"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
