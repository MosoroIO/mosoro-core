/* ------------------------------------------------------------------ */
/* Robot list with sortable columns and filtering                      */
/* ------------------------------------------------------------------ */

import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import type {
  FleetStatusResponse,
  RobotStatusResponse,
  SortConfig,
  SortDirection,
} from "../../types/robot";

interface RobotListProps {
  fleetData: FleetStatusResponse | null;
  isLoading: boolean;
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

function formatTimestamp(ts: number): string {
  return new Date(ts * 1000).toLocaleString();
}

type SortableKey = keyof Pick<
  RobotStatusResponse,
  "robot_id" | "vendor" | "status" | "battery" | "health" | "last_updated"
>;

const SORTABLE_COLUMNS: { key: SortableKey; label: string }[] = [
  { key: "robot_id", label: "Robot ID" },
  { key: "vendor", label: "Vendor" },
  { key: "status", label: "Status" },
  { key: "battery", label: "Battery" },
  { key: "health", label: "Health" },
  { key: "last_updated", label: "Last Updated" },
];

function sortRobots(
  robots: RobotStatusResponse[],
  sortConfig: SortConfig,
): RobotStatusResponse[] {
  const sorted = [...robots];
  const { key, direction } = sortConfig;
  const multiplier = direction === "asc" ? 1 : -1;

  sorted.sort((a, b) => {
    const aVal = a[key as keyof RobotStatusResponse];
    const bVal = b[key as keyof RobotStatusResponse];

    if (aVal === null || aVal === undefined) return 1;
    if (bVal === null || bVal === undefined) return -1;

    if (typeof aVal === "string" && typeof bVal === "string") {
      return aVal.localeCompare(bVal) * multiplier;
    }

    if (typeof aVal === "number" && typeof bVal === "number") {
      return (aVal - bVal) * multiplier;
    }

    return 0;
  });

  return sorted;
}

function RobotList({ fleetData, isLoading }: RobotListProps) {
  const [sortConfig, setSortConfig] = useState<SortConfig>({
    key: "robot_id",
    direction: "asc",
  });
  const [vendorFilter, setVendorFilter] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState<string>("");

  const vendors = useMemo(() => {
    if (!fleetData) return [];
    return Object.keys(fleetData.by_vendor).sort();
  }, [fleetData]);

  const statuses = useMemo(() => {
    if (!fleetData) return [];
    return Object.keys(fleetData.by_status).sort();
  }, [fleetData]);

  const filteredAndSorted = useMemo(() => {
    if (!fleetData) return [];

    let robots = fleetData.robots;

    if (vendorFilter) {
      robots = robots.filter((r) => r.vendor === vendorFilter);
    }

    if (statusFilter) {
      robots = robots.filter((r) => r.status === statusFilter);
    }

    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      robots = robots.filter(
        (r) =>
          r.robot_id.toLowerCase().includes(q) ||
          r.vendor.toLowerCase().includes(q),
      );
    }

    return sortRobots(robots, sortConfig);
  }, [fleetData, vendorFilter, statusFilter, searchQuery, sortConfig]);

  function handleSort(key: string) {
    setSortConfig((prev) => {
      const direction: SortDirection =
        prev.key === key && prev.direction === "asc" ? "desc" : "asc";
      return { key, direction };
    });
  }

  function getSortIndicator(key: string): string {
    if (sortConfig.key !== key) return "";
    return sortConfig.direction === "asc" ? " ↑" : " ↓";
  }

  if (isLoading || !fleetData) {
    return (
      <div className="flex items-center justify-center py-20" role="status">
        <p className="text-sm text-[var(--color-text-secondary)]">
          Loading robots…
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4 animate-fade-in">
      {/* Filters */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <input
          type="search"
          placeholder="Search robots…"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="input max-w-xs"
          aria-label="Search robots"
        />

        <select
          value={vendorFilter}
          onChange={(e) => setVendorFilter(e.target.value)}
          className="input max-w-[180px]"
          aria-label="Filter by vendor"
        >
          <option value="">All Vendors</option>
          {vendors.map((v) => (
            <option key={v} value={v}>
              {v}
            </option>
          ))}
        </select>

        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="input max-w-[180px]"
          aria-label="Filter by status"
        >
          <option value="">All Statuses</option>
          {statuses.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>

        <span className="text-xs text-[var(--color-text-muted)]">
          {filteredAndSorted.length} of {fleetData.total_robots} robots
        </span>
      </div>

      {/* Table */}
      <div className="card overflow-x-auto p-0">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-border bg-surface-secondary text-xs uppercase text-[var(--color-text-muted)]">
              {SORTABLE_COLUMNS.map((col) => (
                <th
                  key={col.key}
                  className="cursor-pointer select-none px-4 py-3 font-medium hover:text-[var(--color-text-primary)] transition-colors"
                  onClick={() => handleSort(col.key)}
                  aria-sort={
                    sortConfig.key === col.key
                      ? sortConfig.direction === "asc"
                        ? "ascending"
                        : "descending"
                      : "none"
                  }
                >
                  {col.label}
                  {getSortIndicator(col.key)}
                </th>
              ))}
              <th className="px-4 py-3 font-medium">Online</th>
            </tr>
          </thead>
          <tbody>
            {filteredAndSorted.length === 0 ? (
              <tr>
                <td
                  colSpan={7}
                  className="px-4 py-8 text-center text-[var(--color-text-muted)]"
                >
                  No robots match the current filters.
                </td>
              </tr>
            ) : (
              filteredAndSorted.map((robot) => (
                <tr
                  key={robot.robot_id}
                  className="border-b border-border/50 last:border-0 hover:bg-surface-tertiary/50 transition-colors"
                >
                  <td className="px-4 py-3">
                    <Link
                      to={`/robots/${encodeURIComponent(robot.robot_id)}`}
                      className="font-mono text-xs text-primary-500 hover:underline"
                    >
                      {robot.robot_id}
                    </Link>
                  </td>
                  <td className="px-4 py-3 capitalize">{robot.vendor}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`badge ${getStatusBadgeClass(robot.status)}`}
                    >
                      {robot.status || "unknown"}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {robot.battery !== null ? (
                      <div className="flex items-center gap-2">
                        <div className="h-1.5 w-16 overflow-hidden rounded-full bg-surface-tertiary">
                          <div
                            className="h-full rounded-full transition-all duration-300"
                            style={{
                              width: `${Math.min(robot.battery, 100)}%`,
                              backgroundColor:
                                robot.battery > 50
                                  ? "var(--color-success)"
                                  : robot.battery > 20
                                    ? "var(--color-warning)"
                                    : "var(--color-danger)",
                            }}
                          />
                        </div>
                        <span className="text-xs">
                          {Math.round(robot.battery)}%
                        </span>
                      </div>
                    ) : (
                      <span className="text-[var(--color-text-muted)]">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3 capitalize">
                    {robot.health || "—"}
                  </td>
                  <td className="px-4 py-3 text-xs text-[var(--color-text-muted)]">
                    {formatTimestamp(robot.last_updated)}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-block h-2.5 w-2.5 rounded-full ${
                        robot.is_online
                          ? "bg-[var(--color-success)]"
                          : "bg-[var(--color-danger)]"
                      }`}
                      aria-label={robot.is_online ? "Online" : "Offline"}
                    />
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export { RobotList };
