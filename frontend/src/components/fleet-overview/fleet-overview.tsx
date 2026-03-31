/* ------------------------------------------------------------------ */
/* Fleet overview component — animated summary cards + chart breakdowns */
/* ------------------------------------------------------------------ */

import { useMemo } from "react";
import { motion } from "framer-motion";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import { Link } from "react-router-dom";
import { SummaryCard, SummaryCardSkeleton } from "./summary-card";
import { SkeletonPulse } from "../ui/skeleton";
import type { FleetStatusResponse } from "../../types/robot";
import { VENDOR_COLORS, STATUS_COLORS } from "../../types/robot";

interface FleetOverviewProps {
  fleetData: FleetStatusResponse | null;
  isLoading: boolean;
}

/* ------------------------------------------------------------------ */
/* Generate mock trend data for sparklines                              */
/* ------------------------------------------------------------------ */
function generateTrend(current: number, variance: number = 3): number[] {
  const points: number[] = [];
  for (let i = 0; i < 12; i++) {
    const noise = Math.round((Math.random() - 0.5) * variance * 2);
    points.push(Math.max(0, current + noise - Math.round(variance * (1 - i / 12))));
  }
  points.push(current);
  return points;
}

/* ------------------------------------------------------------------ */
/* Donut chart breakdown component                                      */
/* ------------------------------------------------------------------ */
function ChartBreakdown({
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

  const chartData = entries.map(([name, value]) => ({
    name,
    value,
    color: colorMap[name] || "#6b7280",
  }));

  return (
    <motion.div
      className="card"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.3 }}
    >
      <h3 className="mb-3 text-sm font-semibold text-[var(--color-text-primary)]">
        {title}
      </h3>

      <div className="flex flex-col items-center gap-4 sm:flex-row">
        {/* Donut chart */}
        <div className="h-36 w-36 shrink-0">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                innerRadius={36}
                outerRadius={60}
                paddingAngle={2}
                dataKey="value"
                stroke="none"
                isAnimationActive={true}
                animationBegin={200}
                animationDuration={800}
              >
                {chartData.map((entry) => (
                  <Cell key={entry.name} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: "var(--color-surface)",
                  border: "1px solid var(--color-border)",
                  borderRadius: "8px",
                  fontSize: "12px",
                  color: "var(--color-text-primary)",
                }}
                formatter={(value: number | string | readonly (string | number)[] | undefined, name: string | number | undefined) => {
                  const numValue = typeof value === 'number' ? value : 0;
                  const displayName = String(name ?? '');
                  return [
                    `${numValue} (${total > 0 ? Math.round((numValue / total) * 100) : 0}%)`,
                    displayName,
                  ];
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Legend */}
        <div className="flex flex-1 flex-wrap gap-x-4 gap-y-1.5">
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
    </motion.div>
  );
}

/* ------------------------------------------------------------------ */
/* Skeleton for chart breakdown                                         */
/* ------------------------------------------------------------------ */
function ChartBreakdownSkeleton() {
  return (
    <div className="card">
      <SkeletonPulse className="mb-3 h-4 w-24 rounded-md" />
      <div className="flex flex-col items-center gap-4 sm:flex-row">
        <SkeletonPulse className="h-36 w-36 shrink-0 rounded-full" />
        <div className="flex flex-1 flex-wrap gap-x-4 gap-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="flex items-center gap-1.5">
              <SkeletonPulse className="h-2.5 w-2.5 rounded-full" />
              <SkeletonPulse className="h-3 w-16 rounded-md" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Main fleet overview component                                        */
/* ------------------------------------------------------------------ */
function FleetOverview({ fleetData, isLoading }: FleetOverviewProps) {
  // Compute derived values
  const stats = useMemo(() => {
    if (!fleetData) return null;

    const onlineCount = fleetData.robots.filter((r) => r.is_online).length;
    const offlineCount = fleetData.total_robots - onlineCount;
    const avgBattery = fleetData.robots.reduce((sum, r) => sum + (r.battery ?? 0), 0);
    const avgBatteryValue =
      fleetData.total_robots > 0
        ? Math.round(avgBattery / fleetData.total_robots)
        : 0;
    const errorCount = fleetData.by_status["error"] || 0;

    return { onlineCount, offlineCount, avgBatteryValue, errorCount };
  }, [fleetData]);

  /* Loading state — skeleton placeholders */
  if (isLoading || !fleetData || !stats) {
    return (
      <div className="space-y-6" role="status" aria-label="Loading fleet data">
        {/* Skeleton summary cards */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <SummaryCardSkeleton key={i} index={i} />
          ))}
        </div>

        {/* Skeleton breakdowns */}
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <ChartBreakdownSkeleton />
          <ChartBreakdownSkeleton />
        </div>

        {/* Skeleton table */}
        <div className="card p-0 overflow-hidden">
          <div className="px-4 py-3">
            <SkeletonPulse className="h-4 w-32 rounded-md" />
          </div>
          {Array.from({ length: 5 }).map((_, i) => (
            <div
              key={i}
              className="flex gap-4 border-t border-border/50 px-4 py-3"
            >
              <SkeletonPulse className="h-3 w-24 rounded-md" />
              <SkeletonPulse className="h-3 w-16 rounded-md" />
              <SkeletonPulse className="h-3 w-14 rounded-md" />
              <SkeletonPulse className="h-3 w-12 rounded-md" />
              <SkeletonPulse className="h-3 w-8 rounded-md" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Summary cards with staggered entrance */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <SummaryCard
          title="Total Robots"
          value={fleetData.total_robots}
          subtitle={`${stats.onlineCount} online, ${stats.offlineCount} offline`}
          icon="🤖"
          accentColor="var(--color-primary-500)"
          trendData={generateTrend(fleetData.total_robots, 2)}
          index={0}
        />
        <SummaryCard
          title="Online"
          value={stats.onlineCount}
          subtitle={`${fleetData.total_robots > 0 ? Math.round((stats.onlineCount / fleetData.total_robots) * 100) : 0}% of fleet`}
          icon="✅"
          accentColor="var(--color-success)"
          trendData={generateTrend(stats.onlineCount, 2)}
          index={1}
        />
        <SummaryCard
          title="Avg Battery"
          value={`${stats.avgBatteryValue}%`}
          subtitle="Across all robots"
          icon="🔋"
          accentColor="var(--color-warning)"
          trendData={generateTrend(stats.avgBatteryValue, 8)}
          index={2}
        />
        <SummaryCard
          title="Errors"
          value={stats.errorCount}
          subtitle={stats.errorCount > 0 ? "Needs attention" : "All clear"}
          icon="⚠️"
          accentColor={stats.errorCount > 0 ? "var(--color-danger)" : "var(--color-success)"}
          trendData={generateTrend(stats.errorCount, 1)}
          index={3}
        />
      </div>

      {/* Chart breakdowns */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <ChartBreakdown
          data={fleetData.by_status}
          colorMap={STATUS_COLORS}
          title="By Status"
        />
        <ChartBreakdown
          data={fleetData.by_vendor}
          colorMap={VENDOR_COLORS}
          title="By Vendor"
        />
      </div>

      {/* Quick robot list */}
      <motion.div
        className="card"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.4 }}
      >
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
              {fleetData.robots.slice(0, 10).map((robot, idx) => (
                <motion.tr
                  key={robot.robot_id}
                  className="border-b border-border/50 last:border-0"
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.25, delay: 0.45 + idx * 0.03 }}
                >
                  <td className="py-2 pr-4">
                    <Link
                      to={`/robots/${encodeURIComponent(robot.robot_id)}`}
                      className="font-mono text-xs text-primary-500 hover:underline"
                    >
                      {robot.robot_id}
                    </Link>
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
                </motion.tr>
              ))}
            </tbody>
          </table>
          {fleetData.robots.length > 10 && (
            <p className="mt-2 text-xs text-[var(--color-text-muted)]">
              Showing 10 of {fleetData.robots.length} robots
            </p>
          )}
        </div>
      </motion.div>
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
