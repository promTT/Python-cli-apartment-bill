// Thin fetch wrapper: attaches the JWT, parses JSON, surfaces errors.
const API_BASE = "/api";

export function getToken() {
  return localStorage.getItem("token");
}

export function setToken(token) {
  if (token) localStorage.setItem("token", token);
  else localStorage.removeItem("token");
}

export function clearToken() {
  localStorage.removeItem("token");
}

async function request(path, { method = "GET", body } = {}) {
  const headers = { "Content-Type": "application/json" };
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (res.status === 401) {
    clearToken();
    window.dispatchEvent(new Event("auth:logout"));
    throw new Error("Session expired — please log in again.");
  }

  const text = await res.text();
  let data = {};
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    data = {};
  }
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
  return data;
}

export const api = {
  login: (username, password) =>
    request("/auth/login", { method: "POST", body: { username, password } }),
  me: () => request("/auth/me"),

  state: () => request("/state"),
  newCycle: (billing_month, bill_date) =>
    request("/cycle/new", { method: "POST", body: { billing_month, bill_date } }),
  meters: () => request("/meters"),
  saveMeters: (rooms) =>
    request("/meters/current", { method: "PUT", body: { rooms } }),

  drcDetect: () => request("/drc/detect", { method: "POST" }),
  drcApply: (fixes) =>
    request("/drc/apply", { method: "POST", body: { fixes } }),

  generateBill: () => request("/bills/generate", { method: "POST" }),
  downloadPdf: async () => {
    const headers = {};
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
    const res = await fetch(`${API_BASE}/bills/pdf`, { headers });
    if (!res.ok) throw new Error("PDF not available.");
    return res.blob();
  },
  convertPdf: () => request("/bills/convert", { method: "POST" }),

  upload: () => request("/upload", { method: "POST" }),
  uploadedUrls: () => request("/uploaded_urls"),
  send: () => request("/send", { method: "POST" }),
};
