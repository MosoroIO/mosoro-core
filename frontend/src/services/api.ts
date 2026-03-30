/* ------------------------------------------------------------------ */
/* Centralized API client for the Mosoro backend                       */
/* ------------------------------------------------------------------ */

import type {
  EventResponse,
  FleetStatusResponse,
  HealthResponse,
  RobotStatusResponse,
  TaskAssignRequest,
  TaskAssignResponse,
  TokenRequest,
  TokenResponse,
} from "../types/robot";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const TOKEN_KEY = "mosoro_access_token";

/* ------------------------------------------------------------------ */
/* Token helpers                                                       */
/* ------------------------------------------------------------------ */

function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

function storeToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

/* ------------------------------------------------------------------ */
/* Core fetch wrapper                                                  */
/* ------------------------------------------------------------------ */

async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = getStoredToken();

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    clearToken();
    window.location.href = "/login";
    throw new Error("Authentication expired. Please log in again.");
  }

  if (!response.ok) {
    const errorBody = await response.text().catch(() => "Unknown error");
    throw new Error(
      `API error ${response.status}: ${response.statusText} — ${errorBody}`,
    );
  }

  return response.json() as Promise<T>;
}

/* ------------------------------------------------------------------ */
/* Auth endpoints                                                      */
/* ------------------------------------------------------------------ */

async function login(credentials: TokenRequest): Promise<TokenResponse> {
  const data = await apiFetch<TokenResponse>("/auth/token", {
    method: "POST",
    body: JSON.stringify(credentials),
  });
  storeToken(data.access_token);
  return data;
}

function logout(): void {
  clearToken();
}

function isAuthenticated(): boolean {
  return getStoredToken() !== null;
}

/* ------------------------------------------------------------------ */
/* Health                                                               */
/* ------------------------------------------------------------------ */

async function getHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>("/health");
}

/* ------------------------------------------------------------------ */
/* Fleet / Robots                                                      */
/* ------------------------------------------------------------------ */

async function getFleetStatus(): Promise<FleetStatusResponse> {
  return apiFetch<FleetStatusResponse>("/robots");
}

async function getRobotStatus(robotId: string): Promise<RobotStatusResponse> {
  return apiFetch<RobotStatusResponse>(`/robots/${encodeURIComponent(robotId)}`);
}

/* ------------------------------------------------------------------ */
/* Tasks                                                               */
/* ------------------------------------------------------------------ */

async function assignTask(
  task: TaskAssignRequest,
): Promise<TaskAssignResponse> {
  return apiFetch<TaskAssignResponse>("/tasks", {
    method: "POST",
    body: JSON.stringify(task),
  });
}

/* ------------------------------------------------------------------ */
/* Events                                                              */
/* ------------------------------------------------------------------ */

async function getEvents(): Promise<EventResponse[]> {
  return apiFetch<EventResponse[]>("/events");
}

/* ------------------------------------------------------------------ */
/* Public API                                                          */
/* ------------------------------------------------------------------ */

export const api = {
  login,
  logout,
  isAuthenticated,
  getStoredToken,
  getHealth,
  getFleetStatus,
  getRobotStatus,
  assignTask,
  getEvents,
  API_BASE_URL,
} as const;
