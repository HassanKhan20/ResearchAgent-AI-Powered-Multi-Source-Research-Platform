import type { Job, JobDetail, JobSummary, StreamEvent } from "./types";

const BASE = import.meta.env.VITE_API_URL ?? "";
const TOKEN_KEY = "researchagent.token";

function readToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

function writeToken(token: string | null) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* storage unavailable: session lives in memory only */
  }
}

let token: string | null = readToken();
let pending: Promise<string> | null = null;

async function createSession(): Promise<string> {
  const res = await fetch(`${BASE}/api/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
  if (!res.ok) throw new Error("Could not start a session");
  const body = await res.json();
  token = body.token as string;
  writeToken(token);
  return token;
}

export async function ensureSession(): Promise<string> {
  if (token) return token;
  pending ??= createSession().finally(() => (pending = null));
  return pending;
}

async function request<T>(path: string, init: RequestInit = {}, retry = true): Promise<T> {
  const t = await ensureSession();
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${t}`, ...init.headers },
  });
  if (res.status === 401 && retry) {
    token = null;
    writeToken(null);
    return request<T>(path, init, false);
  }
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(typeof detail.detail === "string" ? detail.detail : `Request failed (${res.status})`);
  }
  return (res.status === 204 ? undefined : await res.json()) as T;
}

export const api = {
  startResearch: (question: string) =>
    request<Job>("/api/research", { method: "POST", body: JSON.stringify({ question }) }),
  listResearch: () => request<JobSummary[]>("/api/research"),
  getResearch: (id: string) => request<JobDetail>(`/api/research/${id}`),
  deleteResearch: (id: string) => request<void>(`/api/research/${id}`, { method: "DELETE" }),
};

export async function streamEvents(jobId: string, onEvent: (e: StreamEvent) => void): Promise<() => void> {
  const t = await ensureSession();
  const source = new EventSource(`${BASE}/api/research/${jobId}/events?token=${encodeURIComponent(t)}`);
  const handler = (msg: MessageEvent) => {
    const event = JSON.parse(msg.data) as StreamEvent;
    onEvent(event);
    if (event.type === "done" || event.type === "error") source.close();
  };
  for (const name of ["step", "status", "done", "error"]) source.addEventListener(name, handler);
  return () => source.close();
}
