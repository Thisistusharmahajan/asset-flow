import { useEffect, useState } from "react";
import { api } from "../api";
import { useAuth } from "../AuthContext";
import Sidebar from "../components/Sidebar";
import "./OrganizationSetup.css";

const TABS = [
  { key: "departments", label: "Departments" },
  { key: "categories", label: "Categories" },
  { key: "employees", label: "Employee" },
];

const ROLES = ["Admin", "AssetManager", "DepartmentHead", "Employee"];

export default function OrganizationSetup() {
  const { user } = useAuth();
  const [tab, setTab] = useState("departments");

  const [departments, setDepartments] = useState([]);
  const [categories, setCategories] = useState([]);
  const [employees, setEmployees] = useState([]);

  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const [modal, setModal] = useState(null); // { type: 'department'|'category', record?: {...} }
  const [saving, setSaving] = useState(false);

  const isAdmin = user?.role === "Admin";

  function loadAll() {
    setLoading(true);
    Promise.all([api.departments(), api.categories(), api.employees()])
      .then(([d, c, e]) => {
        setDepartments(d);
        setCategories(c);
        setEmployees(e);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    if (isAdmin) loadAll();
    else setLoading(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAdmin]);

  function openAdd() {
    if (tab === "departments") setModal({ type: "department", record: null });
    else if (tab === "categories") setModal({ type: "category", record: null });
  }

  function openEditDepartment(dep) {
    setModal({ type: "department", record: dep });
  }

  function openEditCategory(cat) {
    setModal({ type: "category", record: cat });
  }

  async function handleSaveDepartment(form) {
    setSaving(true);
    setError("");
    try {
      if (form.id) {
        const updated = await api.updateDepartment(form.id, {
          name: form.name,
          parent_department_id: form.parent_department_id || null,
          head_employee_id: form.head_employee_id || null,
          status: form.status,
        });
        setDepartments((prev) => prev.map((d) => (d.id === updated.id ? updated : d)));
      } else {
        const created = await api.createDepartment({
          name: form.name,
          parent_department_id: form.parent_department_id || null,
          head_employee_id: form.head_employee_id || null,
          status: form.status,
        });
        setDepartments((prev) => [...prev, created].sort((a, b) => a.name.localeCompare(b.name)));
      }
      setModal(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleSaveCategory(form) {
    setSaving(true);
    setError("");
    try {
      if (form.id) {
        const updated = await api.updateCategory(form.id, {
          name: form.name,
          description: form.description,
        });
        setCategories((prev) => prev.map((c) => (c.id === updated.id ? updated : c)));
      } else {
        const created = await api.createCategory({
          name: form.name,
          description: form.description,
        });
        setCategories((prev) => [...prev, created].sort((a, b) => a.name.localeCompare(b.name)));
      }
      setModal(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleRoleChange(emp, role) {
    setError("");
    try {
      const updated = await api.updateEmployeeRole(emp.id, role);
      setEmployees((prev) => prev.map((e) => (e.id === updated.id ? updated : e)));
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleEmployeeStatusToggle(emp) {
    setError("");
    const nextStatus = emp.status === "Active" ? "Inactive" : "Active";
    try {
      const updated = await api.updateEmployee(emp.id, { status: nextStatus });
      setEmployees((prev) => prev.map((e) => (e.id === updated.id ? updated : e)));
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleEmployeeDepartmentChange(emp, department_id) {
    setError("");
    try {
      const updated = await api.updateEmployee(emp.id, { department_id: department_id || null });
      setEmployees((prev) => prev.map((e) => (e.id === updated.id ? updated : e)));
    } catch (err) {
      setError(err.message);
    }
  }

  if (!isAdmin) {
    return (
      <div className="shell">
        <Sidebar active="Organization setup" />
        <main className="content">
          <header className="content-header">
            <h1>Organization setup</h1>
          </header>
          <div className="banner banner-error">
            This screen is available to Admins only.
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="shell">
      <Sidebar active="Organization setup" />
      <main className="content">
        <header className="content-header">
          <h1>Organization setup</h1>
          <span className="content-sub">Admin only</span>
        </header>

        {error && <div className="banner banner-error">{error}</div>}

        <div className="org-toolbar">
          <div className="org-tabs">
            {TABS.map((t) => (
              <button
                key={t.key}
                className={"org-tab" + (tab === t.key ? " active" : "")}
                onClick={() => setTab(t.key)}
              >
                {t.label}
              </button>
            ))}
          </div>
          {tab !== "employees" && (
            <button className="org-add-btn" onClick={openAdd}>
              + Add
            </button>
          )}
        </div>

        {loading ? (
          <p className="empty-state">Loading…</p>
        ) : (
          <div className="org-panel">
            {tab === "departments" && (
              <table className="org-table">
                <thead>
                  <tr>
                    <th>Department</th>
                    <th>Head</th>
                    <th>Parent Dept</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {departments.length === 0 && (
                    <tr>
                      <td className="empty-state" colSpan={4}>
                        No departments yet — add one to get started.
                      </td>
                    </tr>
                  )}
                  {departments.map((d) => (
                    <tr key={d.id} onClick={() => openEditDepartment(d)}>
                      <td className="org-cell-primary">{d.name}</td>
                      <td>{d.head_name || "--"}</td>
                      <td>{d.parent_name || "--"}</td>
                      <td>
                        <span className={"pill pill-" + d.status.toLowerCase()}>
                          {d.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}

            {tab === "categories" && (
              <table className="org-table">
                <thead>
                  <tr>
                    <th>Category</th>
                    <th>Description</th>
                    <th>Assets</th>
                  </tr>
                </thead>
                <tbody>
                  {categories.length === 0 && (
                    <tr>
                      <td className="empty-state" colSpan={3}>
                        No categories yet — add one to get started.
                      </td>
                    </tr>
                  )}
                  {categories.map((c) => (
                    <tr key={c.id} onClick={() => openEditCategory(c)}>
                      <td className="org-cell-primary">{c.name}</td>
                      <td>{c.description || "--"}</td>
                      <td className="org-cell-mono">{c.asset_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}

            {tab === "employees" && (
              <table className="org-table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Email</th>
                    <th>Role</th>
                    <th>Department</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {employees.length === 0 && (
                    <tr>
                      <td className="empty-state" colSpan={5}>
                        No employees found.
                      </td>
                    </tr>
                  )}
                  {employees.map((e) => (
                    <tr key={e.id}>
                      <td className="org-cell-primary">{e.name}</td>
                      <td className="org-cell-mono">{e.email}</td>
                      <td>
                        <select
                          value={e.role}
                          onChange={(ev) => handleRoleChange(e, ev.target.value)}
                          disabled={e.id === user.id}
                        >
                          {ROLES.map((r) => (
                            <option key={r} value={r}>
                              {r}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td>
                        <select
                          value={e.department_id || ""}
                          onChange={(ev) => handleEmployeeDepartmentChange(e, ev.target.value)}
                        >
                          <option value="">--</option>
                          {departments.map((d) => (
                            <option key={d.id} value={d.id}>
                              {d.name}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td>
                        <button
                          className={"pill-toggle pill-" + e.status.toLowerCase()}
                          onClick={() => handleEmployeeStatusToggle(e)}
                          disabled={e.id === user.id}
                        >
                          {e.status}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}

            {tab === "departments" && (
              <p className="org-footnote">
                Editing a department here also drives the picklist in Assets &amp; Allocation.
              </p>
            )}
          </div>
        )}
      </main>

      {modal?.type === "department" && (
        <DepartmentModal
          record={modal.record}
          departments={departments}
          employees={employees}
          saving={saving}
          onCancel={() => setModal(null)}
          onSave={handleSaveDepartment}
        />
      )}

      {modal?.type === "category" && (
        <CategoryModal
          record={modal.record}
          saving={saving}
          onCancel={() => setModal(null)}
          onSave={handleSaveCategory}
        />
      )}
    </div>
  );
}

function DepartmentModal({ record, departments, employees, saving, onCancel, onSave }) {
  const [form, setForm] = useState({
    id: record?.id || null,
    name: record?.name || "",
    parent_department_id: record?.parent_department_id || "",
    head_employee_id: record?.head_employee_id || "",
    status: record?.status || "Active",
  });

  function update(field) {
    return (e) => setForm((f) => ({ ...f, [field]: e.target.value }));
  }

  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <h2>{record ? "Edit department" : "Add department"}</h2>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            onSave(form);
          }}
        >
          <label className="modal-field">
            <span>Department name</span>
            <input type="text" value={form.name} onChange={update("name")} required />
          </label>

          <label className="modal-field">
            <span>Head</span>
            <select value={form.head_employee_id} onChange={update("head_employee_id")}>
              <option value="">--</option>
              {employees.map((e) => (
                <option key={e.id} value={e.id}>
                  {e.name}
                </option>
              ))}
            </select>
          </label>

          <label className="modal-field">
            <span>Parent department</span>
            <select value={form.parent_department_id} onChange={update("parent_department_id")}>
              <option value="">--</option>
              {departments
                .filter((d) => d.id !== form.id)
                .map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
            </select>
          </label>

          <label className="modal-field">
            <span>Status</span>
            <select value={form.status} onChange={update("status")}>
              <option value="Active">Active</option>
              <option value="Inactive">Inactive</option>
            </select>
          </label>

          <div className="modal-actions">
            <button type="button" className="btn-secondary" onClick={onCancel}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={saving}>
              {saving ? "Saving…" : "Save"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function CategoryModal({ record, saving, onCancel, onSave }) {
  const [form, setForm] = useState({
    id: record?.id || null,
    name: record?.name || "",
    description: record?.description || "",
  });

  function update(field) {
    return (e) => setForm((f) => ({ ...f, [field]: e.target.value }));
  }

  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <h2>{record ? "Edit category" : "Add category"}</h2>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            onSave(form);
          }}
        >
          <label className="modal-field">
            <span>Category name</span>
            <input type="text" value={form.name} onChange={update("name")} required />
          </label>

          <label className="modal-field">
            <span>Description</span>
            <textarea rows={3} value={form.description} onChange={update("description")} />
          </label>

          <div className="modal-actions">
            <button type="button" className="btn-secondary" onClick={onCancel}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={saving}>
              {saving ? "Saving…" : "Save"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
