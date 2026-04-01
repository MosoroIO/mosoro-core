/* ------------------------------------------------------------------ */
/* TypeScript interfaces matching the Mosoro API models                */
/* ------------------------------------------------------------------ */

export interface Position {
  x: number;
  y: number;
  z?: number;
  theta?: number;
  map_id?: string;
}

export interface CurrentTask {
  task_id: string;
  task_type: string;
  progress?: number;
}

export interface RobotStatusResponse {
  robot_id: string;
  vendor: string;
  status: string | null;
  position: Position | null;
  battery: number | null;
  health: string | null;
  current_task: CurrentTask | null;
  last_updated: number;
  is_online: boolean;
}

export interface FleetStatusResponse {
  total_robots: number;
  robots: RobotStatusResponse[];
  by_vendor: Record<string, number>;
  by_status: Record<string, number>;
}

export interface EventResponse {
  robot_id: string;
  vendor: string;
  topic: string;
  payload: Record<string, unknown>;
  received_at: number;
}

export interface TaskAssignRequest {
  robot_id: string;
  action: string;
  position?: Position | null;
  parameters?: Record<string, unknown> | null;
}

export interface TaskAssignResponse {
  success: boolean;
  message: string;
  task_id: string | null;
  robot_id: string;
}

export interface TokenRequest {
  username: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface HealthResponse {
  status: string;
  version: string;
  mqtt_connected: boolean;
  fleet_size: number;
  uptime_seconds: number;
}

/* ------------------------------------------------------------------ */
/* WebSocket message types                                             */
/* ------------------------------------------------------------------ */

export type WebSocketMessageType =
  | "initial_state"
  | "robot_update"
  | "heartbeat"
  | "event"
  | "notification";

export interface NotificationRecord {
  id: string;
  robot_id: string;
  vendor: string;
  event_type: "offline" | "error" | "task_failed" | string;
  message: string;
  timestamp: number;
  read: boolean;
}

export interface WebSocketMessage {
  type: WebSocketMessageType;
  data: FleetStatusResponse | RobotStatusResponse | EventResponse | NotificationRecord | null;
  timestamp?: number;
}

/* ------------------------------------------------------------------ */
/* UI-specific types                                                   */
/* ------------------------------------------------------------------ */

export type RobotStatus =
  | "idle"
  | "moving"
  | "working"
  | "charging"
  | "error"
  | "offline";

export type ConnectionStatus = "connected" | "connecting" | "disconnected";

export type SortDirection = "asc" | "desc";

export interface SortConfig {
  key: string;
  direction: SortDirection;
}

export type TaskAction = "move_to" | "pick" | "dock" | "pause" | "resume";

export const TASK_ACTIONS: readonly TaskAction[] = [
  "move_to",
  "pick",
  "dock",
  "pause",
  "resume",
] as const;

export const VENDOR_COLORS: Record<string, string> = {
  locus: "#8b5cf6",
  stretch: "#06b6d4",
  seer: "#f59e0b",
  geekplus: "#ec4899",
  mir: "#10b981",
  ur: "#f97316",
  fetch: "#3b82f6",
  other: "#6b7280",
};

export const STATUS_COLORS: Record<string, string> = {
  idle: "#6b7280",
  moving: "#3b82f6",
  working: "#8b5cf6",
  charging: "#f59e0b",
  error: "#ef4444",
  offline: "#374151",
};
