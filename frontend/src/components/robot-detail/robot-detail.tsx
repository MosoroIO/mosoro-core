/* ------------------------------------------------------------------ */
/* Robot detail view — full status, position, task, events             */
/* ------------------------------------------------------------------ */

import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Bot } from "lucide-react";
import { api } from "../../services/api";
import type { EventResponse, RobotStatusResponse } from "../../types/robot";
import { VENDOR_COLORS } from "../../types/robot";

interface RobotDetailProps {
  robotId: string;
  /** Optional live data from WebSocket */
  liveRobot?: RobotStatusResponse | null;
}

function formatTimestamp(ts: number): string {
  return new Date(ts * 1000).toLocaleString();
}

function getStatusBadgeClass(status: string | null): string {
  switch (status) {
    case "idle":
      return "badge-neutral";
    case "moving":
    case "working":
      return "badge-info";
    case "charging":
      return "badge-warning";
    case "error":
      return "badge-danger";
    case "offline":
      return "badge-neutral";
    default:
      return "badge-neutral";
  }
}

function RobotDetail({ robotId, liveRobot }: RobotDetailProps) {
  const [robot, setRobot] = useState<RobotStatusResponse | null>(
    liveRobot || null,
  );
  const [events, setEvents] = useState<EventResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState<string | null>(null);

  const fetchRobot = useCallback(async () => {
    try {
      setIsLoading(true);
      setHasError(null);
      const data = await api.getRobotStatus(robotId);
      setRobot(data);
    } catch (err) {
      setHasError(
        err instanceof Error ? err.message : "Failed to load robot data",
      );
    } finally {
      setIsLoading(false);
    }
  }, [robotId]);

  const fetchEvents = useCallback(async () => {
    try {
      const allEvents = await api.getEvents();
      const robotEvents = allEvents.filter((e) => e.robot_id === robotId);
      setEvents(robotEvents.slice(0, 20));
    } catch {
      // Events are supplementary — don't block the page
    }
  }, [robotId]);

  useEffect(() => {
    fetchRobot();
    fetchEvents();
  }, [fetchRobot, fetchEvents]);

  // Prefer live data when available
  const displayRobot = liveRobot || robot;

  if (isLoading && !displayRobot) {
    return (
      <div className="flex items-center justify-center py-20" role="status">
        <p className="text-sm text-[var(--color-text-secondary)]">
          Loading robot details…
        </p>
      </div>
    );
  }

  if (hasError && !displayRobot) {
    return (
      <div className="card text-center py-12">
        <p className="text-[var(--color-danger)] mb-2">⚠️ {hasError}</p>
        <button onClick={fetchRobot} className="btn-primary text-sm">
          Retry
        </button>
      </div>
    );
  }

  if (!displayRobot) return null;

  const vendorColor = VENDOR_COLORS[displayRobot.vendor] || "#6b7280";

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Breadcrumb */}
      <nav aria-label="Breadcrumb" className="text-sm">
        <ol className="flex items-center gap-2 text-[var(--color-text-muted)]">
          <li>
            <Link to="/robots" className="hover:text-primary-500">
              Robots
            </Link>
          </li>
          <li aria-hidden="true">/</li>
          <li className="text-[var(--color-text-primary)] font-medium">
            {displayRobot.robot_id}
          </li>
        </ol>
      </nav>

      {/* Header */}
      <div className="card flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-4">
          <div
            className="flex h-14 w-14 items-center justify-center rounded-xl"
            style={{ backgroundColor: `${vendorColor}20`, color: vendorColor }}
            aria-hidden="true"
          >
            <Bot className="h-7 w-7" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-[var(--color-text-primary)]">
              {displayRobot.robot_id}
            </h2>
            <p className="text-sm capitalize text-[var(--color-text-secondary)]">
              {displayRobot.vendor}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <span className={`badge ${getStatusBadgeClass(displayRobot.status)}`}>
            {displayRobot.status || "unknown"}
          </span>
          <span
            className={`inline-flex items-center gap-1.5 text-sm ${
              displayRobot.is_online
                ? "text-[var(--color-success)]"
                : "text-[var(--color-danger)]"
            }`}
          >
            <span
              className={`inline-block h-2 w-2 rounded-full ${
                displayRobot.is_online
                  ? "bg-[var(--color-success)]"
                  : "bg-[var(--color-danger)]"
              }`}
              aria-hidden="true"
            />
            {displayRobot.is_online ? "Online" : "Offline"}
          </span>
        </div>
      </div>

      {/* Detail grid */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {/* Battery */}
        <div className="card">
          <h3 className="mb-2 text-xs font-semibold uppercase text-[var(--color-text-muted)]">
            Battery
          </h3>
          {displayRobot.battery !== null ? (
            <div>
              <p className="text-3xl font-bold text-[var(--color-text-primary)]">
                {Math.round(displayRobot.battery)}%
              </p>
              <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-surface-tertiary">
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{
                    width: `${Math.min(displayRobot.battery, 100)}%`,
                    backgroundColor:
                      displayRobot.battery > 50
                        ? "var(--color-success)"
                        : displayRobot.battery > 20
                          ? "var(--color-warning)"
                          : "var(--color-danger)",
                  }}
                />
              </div>
            </div>
          ) : (
            <p className="text-[var(--color-text-muted)]">No data</p>
          )}
        </div>

        {/* Position */}
        <div className="card">
          <h3 className="mb-2 text-xs font-semibold uppercase text-[var(--color-text-muted)]">
            Position
          </h3>
          {displayRobot.position ? (
            <div className="space-y-1 font-mono text-sm">
              <p>
                <span className="text-[var(--color-text-muted)]">X:</span>{" "}
                <span className="text-[var(--color-text-primary)]">
                  {displayRobot.position.x.toFixed(2)}
                </span>
              </p>
              <p>
                <span className="text-[var(--color-text-muted)]">Y:</span>{" "}
                <span className="text-[var(--color-text-primary)]">
                  {displayRobot.position.y.toFixed(2)}
                </span>
              </p>
              {displayRobot.position.z !== undefined &&
                displayRobot.position.z !== null && (
                  <p>
                    <span className="text-[var(--color-text-muted)]">Z:</span>{" "}
                    <span className="text-[var(--color-text-primary)]">
                      {displayRobot.position.z.toFixed(2)}
                    </span>
                  </p>
                )}
              {displayRobot.position.theta !== undefined &&
                displayRobot.position.theta !== null && (
                  <p>
                    <span className="text-[var(--color-text-muted)]">θ:</span>{" "}
                    <span className="text-[var(--color-text-primary)]">
                      {displayRobot.position.theta.toFixed(1)}°
                    </span>
                  </p>
                )}
            </div>
          ) : (
            <p className="text-[var(--color-text-muted)]">No position data</p>
          )}
        </div>

        {/* Health */}
        <div className="card">
          <h3 className="mb-2 text-xs font-semibold uppercase text-[var(--color-text-muted)]">
            Health
          </h3>
          <p className="text-lg font-semibold capitalize text-[var(--color-text-primary)]">
            {displayRobot.health || "Unknown"}
          </p>
          <p className="mt-1 text-xs text-[var(--color-text-muted)]">
            Last updated: {formatTimestamp(displayRobot.last_updated)}
          </p>
        </div>

        {/* Current Task */}
        <div className="card md:col-span-2 xl:col-span-3">
          <h3 className="mb-2 text-xs font-semibold uppercase text-[var(--color-text-muted)]">
            Current Task
          </h3>
          {displayRobot.current_task ? (
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-6">
              <div>
                <span className="text-[var(--color-text-muted)] text-xs">
                  Task ID:
                </span>{" "}
                <span className="font-mono text-sm text-[var(--color-text-primary)]">
                  {displayRobot.current_task.task_id}
                </span>
              </div>
              <div>
                <span className="text-[var(--color-text-muted)] text-xs">
                  Type:
                </span>{" "}
                <span className="text-sm capitalize text-[var(--color-text-primary)]">
                  {displayRobot.current_task.task_type}
                </span>
              </div>
              {displayRobot.current_task.progress !== undefined && (
                <div className="flex items-center gap-2">
                  <span className="text-[var(--color-text-muted)] text-xs">
                    Progress:
                  </span>
                  <div className="h-2 w-32 overflow-hidden rounded-full bg-surface-tertiary">
                    <div
                      className="h-full rounded-full bg-primary-500 transition-all duration-300"
                      style={{
                        width: `${displayRobot.current_task.progress}%`,
                      }}
                    />
                  </div>
                  <span className="text-xs text-[var(--color-text-primary)]">
                    {Math.round(displayRobot.current_task.progress)}%
                  </span>
                </div>
              )}
            </div>
          ) : (
            <p className="text-[var(--color-text-muted)]">No active task</p>
          )}
        </div>
      </div>

      {/* Event history */}
      <div className="card">
        <h3 className="mb-3 text-sm font-semibold text-[var(--color-text-primary)]">
          Recent Events
        </h3>
        {events.length === 0 ? (
          <p className="text-sm text-[var(--color-text-muted)]">
            No events recorded for this robot.
          </p>
        ) : (
          <div className="space-y-2 max-h-80 overflow-y-auto">
            {events.map((event, idx) => (
              <div
                key={`${event.received_at}-${idx}`}
                className="flex items-start gap-3 rounded-md border border-border/50 p-3"
              >
                <span className="text-xs text-[var(--color-text-muted)] whitespace-nowrap">
                  {formatTimestamp(event.received_at)}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-[var(--color-text-primary)]">
                    {event.topic}
                  </p>
                  <pre className="mt-1 overflow-x-auto text-xs text-[var(--color-text-secondary)] font-mono">
                    {JSON.stringify(event.payload, null, 2)}
                  </pre>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export { RobotDetail };
