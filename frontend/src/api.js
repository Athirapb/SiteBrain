// Thin fetch wrapper: bearer token + active site appended to every request.
const state = { token: null, site: null };
// Empty = same origin (dev proxy, or backend serving the built UI)
const API_BASE = (import.meta.env.VITE_API_BASE || "").replace(/\/$/, "") || window.location.origin;

try {
  state.token = localStorage.getItem("sb.token");
  state.site = localStorage.getItem("sb.site");
} catch {
  /* storage unavailable (private mode) — session-only sign-in */
}

export function setToken(t) {
  state.token = t;
  try {
    t ? localStorage.setItem("sb.token", t) : localStorage.removeItem("sb.token");
  } catch {}
}

export function setSite(s) {
  state.site = s;
  try {
    localStorage.setItem("sb.site", s);
  } catch {}
}

export const getToken = () => state.token;
export const getSite = () => state.site;

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

async function request(method, path, body, { site = true } = {}) {
  const url = new URL(path, API_BASE);
  if (site && state.site && !url.searchParams.has("site")) url.searchParams.set("site", state.site);
  const headers = {};
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  let payload;
  if (body instanceof FormData) payload = body;
  else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }
  const res = await fetch(url, { method, headers, body: payload });
  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
  if (!res.ok) {
    const msg = typeof data?.detail === "string" ? data.detail : res.statusText;
    throw new ApiError(res.status, msg);
  }
  return data;
}

// A file the API serves behind sign-in (e.g. an escalation attachment), as a Blob
async function blob(path) {
  const res = await fetch(new URL(path, API_BASE), { headers: state.token ? { Authorization: `Bearer ${state.token}` } : {} });
  if (!res.ok) throw new ApiError(res.status, res.statusText);
  return res.blob();
}

export const api = {
  blob,
  get: (p, o) => request("GET", p, undefined, o),
  post: (p, b, o) => request("POST", p, b ?? {}, o),
  put: (p, b, o) => request("PUT", p, b ?? {}, o),
  del: (p, o) => request("DELETE", p, undefined, o),
};
