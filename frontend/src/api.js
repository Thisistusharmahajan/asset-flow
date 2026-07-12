const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:5000/api";

async function request(path, { method = "GET", body, auth = true } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth) {
    const token = localStorage.getItem("assetflow_token");
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  let data = null;
  try {
    data = await res.json();
  } catch {
    // no body
  }

  if (!res.ok) {
    throw new Error(data?.error || `Request failed (${res.status})`);
  }
  return data;
}

function qs(params = {}) {
  const entries = Object.entries(params).filter(
    ([, v]) => v !== undefined && v !== null && v !== ""
  );
  if (entries.length === 0) return "";
  return "?" + new URLSearchParams(entries).toString();
}

export const api = {
  login: (email, password) =>
    request("/auth/login", { method: "POST", body: { email, password }, auth: false }),
  signup: (name, email, password) =>
    request("/auth/signup", { method: "POST", body: { name, email, password }, auth: false }),
  me: () => request("/auth/me"),
  kpis: () => request("/dashboard/kpis"),
  overdue: () => request("/dashboard/overdue"),
  activity: () => request("/dashboard/activity"),

  // Organization setup (Screen 3)
  departments: (params) => request(`/departments${qs(params)}`),
  createDepartment: (body) => request("/departments", { method: "POST", body }),
  updateDepartment: (id, body) => request(`/departments/${id}`, { method: "PATCH", body }),

  categories: () => request("/asset-categories"),
  createCategory: (body) => request("/asset-categories", { method: "POST", body }),
  updateCategory: (id, body) => request(`/asset-categories/${id}`, { method: "PATCH", body }),

  employees: (params) => request(`/employees${qs(params)}`),
  updateEmployeeRole: (id, role) =>
    request(`/employees/${id}/role`, { method: "PATCH", body: { role } }),
  updateEmployee: (id, body) => request(`/employees/${id}`, { method: "PATCH", body }),

  // Assets (Screen 4)
  assets: (params) => request(`/assets${qs(params)}`),
  asset: (id) => request(`/assets/${id}`),
  createAsset: (body) => request("/assets", { method: "POST", body }),
  updateAsset: (id, body) => request(`/assets/${id}`, { method: "PATCH", body }),
  assetHistory: (id) => request(`/assets/${id}/history`),
};
