/* ------------------------------------------------------------------ */
/* React hook for fleet WebSocket connection                           */
/* ------------------------------------------------------------------ */

import { useCallback, useEffect, useRef, useState } from "react";
import { createFleetWebSocket } from "../services/websocket";
import type {
  ConnectionStatus,
  FleetStatusResponse,
  RobotStatusResponse,
  WebSocketMessage,
} from "../types/robot";
import { api } from "../services/api";

interface UseWebSocketReturn {
  fleetData: FleetStatusResponse | null;
  connectionStatus: ConnectionStatus;
  connect: () => void;
  disconnect: () => void;
}

function useFleetWebSocket(): UseWebSocketReturn {
  const [fleetData, setFleetData] = useState<FleetStatusResponse | null>(null);
  const [connectionStatus, setConnectionStatus] =
    useState<ConnectionStatus>("disconnected");

  const wsRef = useRef<ReturnType<typeof createFleetWebSocket> | null>(null);

  const handleMessage = useCallback((message: WebSocketMessage) => {
    switch (message.type) {
      case "initial_state":
        setFleetData(message.data as FleetStatusResponse);
        break;

      case "robot_update": {
        const updatedRobot = message.data as RobotStatusResponse;
        setFleetData((prev) => {
          if (!prev) return prev;

          const robotIndex = prev.robots.findIndex(
            (r) => r.robot_id === updatedRobot.robot_id,
          );

          let updatedRobots: RobotStatusResponse[];
          if (robotIndex >= 0) {
            updatedRobots = [...prev.robots];
            updatedRobots[robotIndex] = updatedRobot;
          } else {
            updatedRobots = [...prev.robots, updatedRobot];
          }

          // Recompute aggregates
          const byVendor: Record<string, number> = {};
          const byStatus: Record<string, number> = {};
          for (const robot of updatedRobots) {
            byVendor[robot.vendor] = (byVendor[robot.vendor] || 0) + 1;
            const status = robot.status || "unknown";
            byStatus[status] = (byStatus[status] || 0) + 1;
          }

          return {
            total_robots: updatedRobots.length,
            robots: updatedRobots,
            by_vendor: byVendor,
            by_status: byStatus,
          };
        });
        break;
      }

      case "heartbeat":
        // Heartbeat acknowledged — no state change needed
        break;

      case "event":
        // Events are handled separately via the events feed
        break;
    }
  }, []);

  const handleStatusChange = useCallback((status: ConnectionStatus) => {
    setConnectionStatus(status);
  }, []);

  const connect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.disconnect();
    }

    const token = api.getStoredToken();
    wsRef.current = createFleetWebSocket({
      onMessage: handleMessage,
      onStatusChange: handleStatusChange,
      token,
    });
    wsRef.current.connect();
  }, [handleMessage, handleStatusChange]);

  const disconnect = useCallback(() => {
    wsRef.current?.disconnect();
  }, []);

  useEffect(() => {
    connect();
    return () => {
      wsRef.current?.disconnect();
    };
  }, [connect]);

  return {
    fleetData,
    connectionStatus,
    connect,
    disconnect,
  };
}

export { useFleetWebSocket };
