/* ------------------------------------------------------------------ */
/* Real-time events feed                                               */
/* ------------------------------------------------------------------ */

import { useCallback, useEffect, useState } from "react";
import { api } from "../../services/api";
import type { EventResponse } from "../../types/robot";
import { VENDOR_COLORS } from "../../types/robot";

const MAX_EVENTS = 100;
const POLL_INTERVAL_MS = 5000;

function formatTimestamp(ts: number): string {
  return new Date(ts * 1000).toLocaleString();
}

function formatRelativeTime(ts: number): string {
  const now = Date.now() / 1000;
  const diff = now - ts;

  if (diff < 60) return `${Math.floor(diff)}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

function EventsFeed() {
  const [events, setEvents] = useState<EventResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState<string | null>(null);
  const [vendorFilter, setVendorFilter] = useState<string>("");
  const [isPaused, setIsPaused] = useState(false);

  const fetchEvents = useCallback(async () => {
    try {
      const data = await api.getEvents();
      setEvents(data.slice(0, MAX_EVENTS));
      setHasError(null);
    } catch (err) {
      setHasError(
        err instanceof Error ? err.message : "Failed to load events",
      );
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchEvents();

    if (!isPaused) {
      const interval = setInterval(fetchEvents, POLL_INTERVAL_MS);
      return () => clearInterval(interval);
    }
  }, [fetchEvents, isPaused]);

  const filteredEvents = vendorFilter
    ? events.filter((e) => e.vendor === vendorFilter)
    : events;

  const vendors = [...new Set(events.map((e) => e.vendor))].sort();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20" role="status">
        <p className="text-sm text-[var(--color-text-secondary)]">
          Loading events…
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4 animate-fade-in">
      {/* Controls */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <select
            value={vendorFilter}
            onChange={(e) => setVendorFilter(e.target.value)}
            className="input max-w-[180px]"
            aria-label="Filter events by vendor"
          >
            <option value="">All Vendors</option>
            {vendors.map((v) => (
              <option key={v} value={v}>
                {v}
              </option>
            ))}
          </select>

          <button
            onClick={() => setIsPaused((p) => !p)}
            className={`btn-secondary text-xs ${isPaused ? "!border-[var(--color-warning)]" : ""}`}
            aria-label={isPaused ? "Resume auto-refresh" : "Pause auto-refresh"}
          >
            {isPaused ? "▶ Resume" : "⏸ Pause"}
          </button>

          <button
            onClick={fetchEvents}
            className="btn-secondary text-xs"
            aria-label="Refresh events"
          >
            🔄 Refresh
          </button>
        </div>

        <span className="text-xs text-[var(--color-text-muted)]">
          {filteredEvents.length} events
          {isPaused && " · Auto-refresh paused"}
        </span>
      </div>

      {/* Error */}
      {hasError && (
        <div
          className="rounded-md bg-red-50 p-3 text-sm text-red-800 dark:bg-red-900/20 dark:text-red-400"
          role="alert"
        >
          ⚠️ {hasError}
        </div>
      )}

      {/* Events list */}
      <div className="space-y-2">
        {filteredEvents.length === 0 ? (
          <div className="card py-12 text-center">
            <p className="text-[var(--color-text-muted)]">
              No events to display.
            </p>
          </div>
        ) : (
          filteredEvents.map((event, idx) => (
            <article
              key={`${event.received_at}-${event.robot_id}-${idx}`}
              className="card flex flex-col gap-2 sm:flex-row sm:items-start sm:gap-4"
            >
              {/* Timestamp */}
              <div className="shrink-0 text-xs text-[var(--color-text-muted)]">
                <time
                  dateTime={new Date(event.received_at * 1000).toISOString()}
                  title={formatTimestamp(event.received_at)}
                >
                  {formatRelativeTime(event.received_at)}
                </time>
              </div>

              {/* Vendor badge */}
              <div className="shrink-0">
                <span
                  className="badge text-white text-[10px]"
                  style={{
                    backgroundColor:
                      VENDOR_COLORS[event.vendor] || "#6b7280",
                  }}
                >
                  {event.vendor}
                </span>
              </div>

              {/* Content */}
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs text-primary-500">
                    {event.robot_id}
                  </span>
                  <span className="text-xs text-[var(--color-text-muted)]">
                    ·
                  </span>
                  <span className="text-sm font-medium text-[var(--color-text-primary)]">
                    {event.topic}
                  </span>
                </div>
                <pre className="mt-1 overflow-x-auto rounded bg-surface-tertiary p-2 text-xs font-mono text-[var(--color-text-secondary)]">
                  {JSON.stringify(event.payload, null, 2)}
                </pre>
              </div>
            </article>
          ))
        )}
      </div>
    </div>
  );
}

export { EventsFeed };
