import type { ApiIncident, Incident, PullRequestReview } from "./model";
import { toIncident } from "./model";

export async function getJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  if (!response.ok) throw new Error(`Request failed (${response.status})`);
  return response.json() as Promise<T>;
}

function controlToken(storageKey: string, prompt: string): string | null {
  const existing = localStorage.getItem(storageKey);
  const token = existing || window.prompt(prompt);
  if (token) localStorage.setItem(storageKey, token);
  return token;
}

export async function controlRequest(
  url: string,
  init: RequestInit,
  errorMessage: string,
): Promise<Response | null> {
  const storageKey = "hive.controlToken";
  const token = controlToken(storageKey, "Hive control token");
  if (!token) return null;
  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${token}`);
  if (init.body) headers.set("Content-Type", "application/json");
  const response = await fetch(url, { ...init, headers });
  if (response.status === 401) localStorage.removeItem(storageKey);
  if (!response.ok) throw new Error(`${errorMessage} (${response.status})`);
  return response;
}

export async function loadIncidents(
  apiBase: string,
  signal?: AbortSignal,
): Promise<Incident[]> {
  const data = await getJson<{ incidents: ApiIncident[] }>(
    `${apiBase}/incidents?limit=200`,
    { cache: "no-store", signal },
  );
  return data.incidents.map(toIncident);
}

export async function loadReviews(
  apiBase: string,
  signal?: AbortSignal,
): Promise<PullRequestReview[]> {
  const data = await getJson<{ reviews: PullRequestReview[] }>(
    `${apiBase}/reviews?limit=100`,
    { cache: "no-store", signal },
  );
  return data.reviews;
}
