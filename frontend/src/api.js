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

export const api = {
  login: (email, password) =>
    request("/auth/login", { method: "POST", body: { email, password }, auth: false }),
  signup: (name, email, password) =>
    request("/auth/signup", { method: "POST", body: { name, email, password }, auth: false }),
  me: () => request("/auth/me"),
  kpis: () => request("/dashboard/kpis"),
  overdue: () => request("/dashboard/overdue"),
  activity: () => request("/dashboard/activity"),
};
