/* ------------------------------------------------------------------ */
/* Robot list with animated rows, status pulse badges, mobile cards     */
/* ------------------------------------------------------------------ */

import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { motion, AnimatePresence, LayoutGroup } from "framer-motion";
import { SkeletonPulse } from "../ui/skeleton";
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

/* ------------------------------------------------------------------ */
/* Status badge helpers                                                 */
/* ------------------------------------------------------------------ */
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

function StatusDot({ status, isOnline }: { status: string | null; isOnline: boolean }) {
  const isError = status === "error";
  const isActive = isOnline && !isError;

  return (
    <span className="relative inline-flex h-2.5 w-2.5">
      {/* Pulse ring for active/error robots */}
      {(isActive || isError) && (
        <span
          className={`absolute inline-flex h-full w-full animate-ping rounded-full opacity-50 ${
            isError ? "bg-[var(--color-danger)]" : "bg-[var(--color-success)]"
          }`}
          style={{ animationDuration: isError ? "1s" : "2s" }}
        />
      )}
      <span
        className={`relative inline-flex h-2.5 w-2.5 rounded-full ${
          isError
            ? "bg-[var(--color-danger)]"
            : isOnline
              ? "bg-[var(--color-success)]"
              : "bg-[var(--color-text-muted)]"
        }`}
        aria-label={isError ? "Error" : isOnline ? "Online" : "Offline"}
      />
    </span>
  );
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

/* ------------------------------------------------------------------ */
/* Skeleton loading state                                               */
/* ------------------------------------------------------------------ */
function RobotListSkeleton() {
  return (
    <div className="space-y-4" role="status" aria-label="Loading robots">
      {/* Filter skeleton */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <SkeletonPulse className="h-9 w-48 rounded-md" />
        <SkeletonPulse className="h-9 w-36 rounded-md" />
        <SkeletonPulse className="h-9 w-36 rounded-md" />
      </div>

      {/* Desktop table skeleton */}
      <div className="card hidden overflow-hidden p-0 md:block">
        <div className="flex gap-4 border-b border-border bg-surface-secondary px-4 py-3">
          {Array.from({ length: 7 }).map((_, i) => (
            <SkeletonPulse
              key={i}
              className="h-3 rounded-md"
              style={{ width: `${100 / 7}%` }}
            />
          ))}
        </div>
        {Array.from({ length: 8 }).map((_, rowIdx) => (
          <div
            key={rowIdx}
            className="flex gap-4 border-b border-border/50 px-4 py-3 last:border-0"
          >
            {Array.from({ length: 7 }).map((_, colIdx) => (
              <SkeletonPulse
                key={colIdx}
                className="h-3 rounded-md"
                style={{ width: `${100 / 7}%` }}
              />
            ))}
          </div>
        ))}
      </div>

      {/* Mobile card skeleton */}
      <div className="space-y-3 md:hidden">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="card space-y-3">
            <div className="flex items-center justify-between">
              <SkeletonPulse className="h-4 w-32 rounded-md" />
              <SkeletonPulse className="h-5 w-16 rounded-full" />
            </div>
            <div className="flex gap-4">
              <SkeletonPulse className="h-3 w-20 rounded-md" />
              <SkeletonPulse className="h-3 w-16 rounded-md" />
            </div>
            <SkeletonPulse className="h-1.5 w-full rounded-full" />
          </div>
        ))}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Mobile card layout for a single robot                                */
/* ------------------------------------------------------------------ */
function RobotCard({ robot }: { robot: RobotStatusResponse }) {
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.2 }}
      className="card"
    >
      <Link
        to={`/robots/${encodeURIComponent(robot.robot_id)}`}
        className="block space-y-2"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <StatusDot status={robot.status} isOnline={robot.is_online} />
            <span className="font-mono text-sm font-medium text-primary-500">
              {robot.robot_id}
            </span>
          </div>
          <span className={`badge ${getStatusBadgeClass(robot.status)}`}>
            {robot.status || "unknown"}
          </span>
        </div>

        <div className="flex items-center gap-4 text-xs text-[var(--color-text-secondary)]">
          <span className="capitalize">{robot.vendor}</span>
          <span className="capitalize">{robot.health || "—"}</span>
        </div>

        {robot.battery !== null && (
          <div className="flex items-center gap-2">
            <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-surface-tertiary">
              <motion.div
                className="h-full rounded-full"
                initial={{ width: 0 }}
                animate={{ width: `${Math.min(robot.battery, 100)}%` }}
                transition={{ duration: 0.6, ease: "easeOut" }}
                style={{
                  backgroundColor:
                    robot.battery > 50
                      ? "var(--color-success)"
                      : robot.battery > 20
                        ? "var(--color-warning)"
                        : "var(--color-danger)",
                }}
              />
            </div>
            <span className="text-xs font-medium text-[var(--color-text-secondary)]">
              {Math.round(robot.battery)}%
            </span>
          </div>
        )}

        <p className="text-xs text-[var(--color-text-muted)]">
          {formatTimestamp(robot.last_updated)}
        </p>
      </Link>
    </motion.div>
  );
}

/* ------------------------------------------------------------------ */
/* Main robot list component                                            */
/* ------------------------------------------------------------------ */
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
    return <RobotListSkeleton />;
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <motion.div
        className="flex flex-col gap-3 sm:flex-row sm:items-center"
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
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
      </motion.div>

      {/* Desktop table */}
      <motion.div
        className="card hidden overflow-x-auto p-0 md:block"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, delay: 0.1 }}
      >
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
          <LayoutGroup>
            <tbody>
              <AnimatePresence mode="popLayout">
                {filteredAndSorted.length === 0 ? (
                  <motion.tr
                    key="empty"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                  >
                    <td
                      colSpan={7}
                      className="px-4 py-8 text-center text-[var(--color-text-muted)]"
                    >
                      No robots match the current filters.
                    </td>
                  </motion.tr>
                ) : (
                  filteredAndSorted.map((robot) => (
                    <motion.tr
                      key={robot.robot_id}
                      layout
                      initial={{ opacity: 0, backgroundColor: "transparent" }}
                      animate={{ opacity: 1, backgroundColor: "transparent" }}
                      exit={{ opacity: 0 }}
                      transition={{ duration: 0.2 }}
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
                              <motion.div
                                className="h-full rounded-full"
                                initial={{ width: 0 }}
                                animate={{
                                  width: `${Math.min(robot.battery, 100)}%`,
                                }}
                                transition={{ duration: 0.6, ease: "easeOut" }}
                                style={{
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
                          <span className="text-[var(--color-text-muted)]">
                            —
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 capitalize">
                        {robot.health || "—"}
                      </td>
                      <td className="px-4 py-3 text-xs text-[var(--color-text-muted)]">
                        {formatTimestamp(robot.last_updated)}
                      </td>
                      <td className="px-4 py-3">
                        <StatusDot
                          status={robot.status}
                          isOnline={robot.is_online}
                        />
                      </td>
                    </motion.tr>
                  ))
                )}
              </AnimatePresence>
            </tbody>
          </LayoutGroup>
        </table>
      </motion.div>

      {/* Mobile card layout */}
      <div className="space-y-3 md:hidden">
        <LayoutGroup>
          <AnimatePresence mode="popLayout">
            {filteredAndSorted.length === 0 ? (
              <motion.p
                key="empty-mobile"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="py-8 text-center text-sm text-[var(--color-text-muted)]"
              >
                No robots match the current filters.
              </motion.p>
            ) : (
              filteredAndSorted.map((robot) => (
                <RobotCard key={robot.robot_id} robot={robot} />
              ))
            )}
          </AnimatePresence>
        </LayoutGroup>
      </div>
    </div>
  );
}

export { RobotList };
