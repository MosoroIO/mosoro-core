/* ------------------------------------------------------------------ */
/* WebSocket service for real-time fleet updates                       */
/* ------------------------------------------------------------------ */

import type { WebSocketMessage } from "../types/robot";

const WS_BASE_URL =
  import.meta.env.VITE_WS_BASE_URL || "ws://localhost:8000";

const RECONNECT_DELAY_MS = 3000;
const MAX_RECONNECT_DELAY_MS = 30000;
const HEARTBEAT_TIMEOUT_MS = 15000;

type MessageHandler = (message: WebSocketMessage) => void;
type StatusHandler = (status: "connected" | "connecting" | "disconnected") => void;

interface FleetWebSocketOptions {
  onMessage: MessageHandler;
  onStatusChange: StatusHandler;
  token?: string | null;
}

/* ------------------------------------------------------------------ */
/* FleetWebSocket class-free manager                                   */
/* ------------------------------------------------------------------ */

function createFleetWebSocket(options: FleetWebSocketOptions) {
  let ws: WebSocket | null = null;
  let reconnectAttempts = 0;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  let heartbeatTimer: ReturnType<typeof setTimeout> | null = null;
  let isManualClose = false;

  function getReconnectDelay(): number {
    const delay = RECONNECT_DELAY_MS * Math.pow(2, reconnectAttempts);
    return Math.min(delay, MAX_RECONNECT_DELAY_MS);
  }

  function resetHeartbeatTimer(): void {
    if (heartbeatTimer) {
      clearTimeout(heartbeatTimer);
    }
    heartbeatTimer = setTimeout(() => {
      // No heartbeat received — connection may be stale
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    }, HEARTBEAT_TIMEOUT_MS);
  }

  function connect(): void {
    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    isManualClose = false;
    options.onStatusChange("connecting");

    const url = options.token
      ? `${WS_BASE_URL}/ws/fleet?token=${encodeURIComponent(options.token)}`
      : `${WS_BASE_URL}/ws/fleet`;

    ws = new WebSocket(url);

    ws.onopen = () => {
      reconnectAttempts = 0;
      options.onStatusChange("connected");
      resetHeartbeatTimer();
    };

    ws.onmessage = (event: MessageEvent) => {
      resetHeartbeatTimer();

      try {
        const message = JSON.parse(event.data as string) as WebSocketMessage;
        options.onMessage(message);
      } catch {
        console.error("[WS] Failed to parse message:", event.data);
      }
    };

    ws.onclose = () => {
      options.onStatusChange("disconnected");

      if (heartbeatTimer) {
        clearTimeout(heartbeatTimer);
        heartbeatTimer = null;
      }

      if (!isManualClose) {
        const delay = getReconnectDelay();
        reconnectAttempts += 1;
        reconnectTimer = setTimeout(connect, delay);
      }
    };

    ws.onerror = () => {
      // onclose will fire after onerror — reconnect handled there
    };
  }

  function disconnect(): void {
    isManualClose = true;

    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }

    if (heartbeatTimer) {
      clearTimeout(heartbeatTimer);
      heartbeatTimer = null;
    }

    if (ws) {
      ws.close();
      ws = null;
    }

    options.onStatusChange("disconnected");
  }

  function isConnected(): boolean {
    return ws !== null && ws.readyState === WebSocket.OPEN;
  }

  return {
    connect,
    disconnect,
    isConnected,
  };
}

export { createFleetWebSocket };
export type { FleetWebSocketOptions };
