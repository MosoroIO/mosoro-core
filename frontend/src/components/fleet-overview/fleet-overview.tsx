/* ------------------------------------------------------------------ */
/* Fleet overview component — summary cards + status breakdown         */
/* ------------------------------------------------------------------ */

import { Bot } from "lucide-react";
import { SummaryCard } from "./summary-card";
import type { FleetStatusResponse } from "../../types/robot";
import { VENDOR_COLORS, STATUS_COLORS } from "../../types/robot";

interface FleetOverviewProps {
  fleetData: FleetStatusResponse | null;
  isLoading: boolean;
}

function StatusBreakdown({
  data,
  colorMap,
  title,
}: {
  data: Record<string, number>;
  colorMap: Record<string, string>;
  title: string;
}) {
  const entries = Object.entries(data).sort(([, a], [, b]) => b - a);
  const total = entries.reduce((sum, [, count]) => sum + count, 0);

  if (entries.length === 0) {
    return null;
  }

  return (
    <div className="card">
      <h3 className="mb-3 text-sm font-semibold text-[var(--color-text-primary)]">
        {title}
      </h3>

      {/* Bar chart */}
      <div className="mb-3 flex h-3 overflow-hidden rounded-full bg-surface-tertiary">
        {entries.map(([key, count]) => (
          <div
            key={key}
            className="transition-all duration-300"
            style={{
              width: `${(count / total) * 100}%`,
              backgroundColor: colorMap[key] || "#6b7280",
            }}
            title={`${key}: ${count}`}
          />
        ))}
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-x-4 gap-y-1">
        {entries.map(([key, count]) => (
          <div key={key} className="flex items-center gap-1.5 text-xs">
            <span
              className="inline-block h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: colorMap[key] || "#6b7280" }}
              aria-hidden="true"
            />
            <span className="capitalize text-[var(--color-text-secondary)]">
              {key}
            </span>
            <span className="font-medium text-[var(--color-text-primary)]">
              {count}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function FleetOverview({ fleetData, isLoading }: FleetOverviewProps) {
  if (isLoading || !fleetData) {
    return (
      <div className="flex items-center justify-center py-20" role="status">
        <div className="text-center">
          <Bot className="mx-auto mb-2 h-10 w-10 text-primary-500 animate-pulse-dot" />
          <p className="text-sm text-[var(--color-text-secondary)]">
            Loading fleet data…
          </p>
        </div>
      </div>
    );
  }

  const onlineCount = fleetData.robots.filter((r) => r.is_online).length;
  const offlineCount = fleetData.total_robots - onlineCount;
  const avgBattery = fleetData.robots.reduce((sum, r) => sum + (r.battery ?? 0), 0);
  const avgBatteryDisplay =
    fleetData.total_robots > 0
      ? `${Math.round(avgBattery / fleetData.total_robots)}%`
      : "N/A";

  const errorCount = fleetData.by_status["error"] || 0;

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Summary cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <SummaryCard
          title="Total Robots"
          value={fleetData.total_robots}
          subtitle={`${onlineCount} online, ${offlineCount} offline`}
          icon="🤖"
          accentColor="var(--color-primary-500)"
        />
        <SummaryCard
          title="Online"
          value={onlineCount}
          subtitle={`${fleetData.total_robots > 0 ? Math.round((onlineCount / fleetData.total_robots) * 100) : 0}% of fleet`}
          icon="✅"
          accentColor="var(--color-success)"
        />
        <SummaryCard
          title="Avg Battery"
          value={avgBatteryDisplay}
          subtitle="Across all robots"
          icon="🔋"
          accentColor="var(--color-warning)"
        />
        <SummaryCard
          title="Errors"
          value={errorCount}
          subtitle={errorCount > 0 ? "Needs attention" : "All clear"}
          icon="⚠️"
          accentColor={errorCount > 0 ? "var(--color-danger)" : "var(--color-success)"}
        />
      </div>

      {/* Breakdowns */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <StatusBreakdown
          data={fleetData.by_status}
          colorMap={STATUS_COLORS}
          title="By Status"
        />
        <StatusBreakdown
          data={fleetData.by_vendor}
          colorMap={VENDOR_COLORS}
          title="By Vendor"
        />
      </div>

      {/* Quick robot list */}
      <div className="card">
        <h3 className="mb-3 text-sm font-semibold text-[var(--color-text-primary)]">
          Fleet at a Glance
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-border text-xs uppercase text-[var(--color-text-muted)]">
                <th className="pb-2 pr-4 font-medium">Robot</th>
                <th className="pb-2 pr-4 font-medium">Vendor</th>
                <th className="pb-2 pr-4 font-medium">Status</th>
                <th className="pb-2 pr-4 font-medium">Battery</th>
                <th className="pb-2 font-medium">Online</th>
              </tr>
            </thead>
            <tbody>
              {fleetData.robots.slice(0, 10).map((robot) => (
                <tr
                  key={robot.robot_id}
                  className="border-b border-border/50 last:border-0"
                >
                  <td className="py-2 pr-4 font-mono text-xs">
                    {robot.robot_id}
                  </td>
                  <td className="py-2 pr-4 capitalize">{robot.vendor}</td>
                  <td className="py-2 pr-4">
                    <span
                      className={`badge ${getStatusBadgeClass(robot.status)}`}
                    >
                      {robot.status || "unknown"}
                    </span>
                  </td>
                  <td className="py-2 pr-4">
                    {robot.battery !== null
                      ? `${Math.round(robot.battery)}%`
                      : "—"}
                  </td>
                  <td className="py-2">
                    <span
                      className={`inline-block h-2 w-2 rounded-full ${
                        robot.is_online
                          ? "bg-[var(--color-success)]"
                          : "bg-[var(--color-danger)]"
                      }`}
                      aria-label={robot.is_online ? "Online" : "Offline"}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {fleetData.robots.length > 10 && (
            <p className="mt-2 text-xs text-[var(--color-text-muted)]">
              Showing 10 of {fleetData.robots.length} robots
            </p>
          )}
        </div>
      </div>
    </div>
  );
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

export { FleetOverview };
