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

  // Allocation & Transfer (Screen 5)
  assetAllocation: (assetId) => request(`/assets/${assetId}/allocation`),
  assetAllocationHistory: (assetId) => request(`/assets/${assetId}/allocation-history`),
  allocateAsset: (assetId, body) => request(`/assets/${assetId}/allocate`, { method: "POST", body }),
  createTransferRequest: (body) => request("/transfer-requests", { method: "POST", body }),
  transferRequests: (params) => request(`/transfer-requests${qs(params)}`),
  resolveTransferRequest: (id, action) =>
    request(`/transfer-requests/${id}`, { method: "PATCH", body: { action } }),

  // Resource booking (Screen 6)
  resources: () => request("/resources"),
  bookings: (params) => request(`/bookings${qs(params)}`),
  createBooking: (body) => request("/bookings", { method: "POST", body }),
  updateBooking: (id, body) => request(`/bookings/${id}`, { method: "PATCH", body }),

  // Maintenance (Screen 7)
  maintenanceRequests: (params) => request(`/maintenance${qs(params)}`),
  createMaintenanceRequest: (body) => request("/maintenance", { method: "POST", body }),
  updateMaintenanceRequest: (id, body) =>
    request(`/maintenance/${id}`, { method: "PATCH", body }),

  // Audit (Screen 8)
  auditCycles: (params) => request(`/audit-cycles${qs(params)}`),
  createAuditCycle: (body) => request("/audit-cycles", { method: "POST", body }),
  auditCycle: (id) => request(`/audit-cycles/${id}`),
  updateAuditItem: (itemId, body) =>
    request(`/audit-cycles/items/${itemId}`, { method: "PATCH", body }),
  closeAuditCycle: (id) => request(`/audit-cycles/${id}/close`, { method: "POST" }),

  // Reports (Screen 9)
  reportUtilizationByDepartment: () => request("/reports/utilization-by-department"),
  reportMaintenanceFrequency: () => request("/reports/maintenance-frequency"),
  reportMostUsed: (params) => request(`/reports/most-used${qs(params)}`),
  reportIdle: (params) => request(`/reports/idle${qs(params)}`),
  reportMaintenanceDue: () => request("/reports/maintenance-due"),
  reportExportUrl: () => `${API_BASE}/reports/export`,

  // Notifications (Screen 10)
  notifications: (params) => request(`/notifications${qs(params)}`),
  markNotificationRead: (id) => request(`/notifications/${id}/read`, { method: "PATCH" }),
  markAllNotificationsRead: () => request("/notifications/mark-all-read", { method: "POST" }),
};