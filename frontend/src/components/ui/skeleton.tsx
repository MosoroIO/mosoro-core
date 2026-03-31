/* ------------------------------------------------------------------ */
/* Reusable skeleton loader with shimmer animation                      */
/* Variants: text, circle, card, table-row                              */
/* ------------------------------------------------------------------ */

import { motion } from "framer-motion";

type SkeletonVariant = "text" | "circle" | "card" | "table-row";

interface SkeletonProps {
  variant?: SkeletonVariant;
  /** Width — CSS value (e.g. "100%", "200px"). Defaults vary by variant. */
  width?: string;
  /** Height — CSS value. Defaults vary by variant. */
  height?: string;
  /** Number of text lines to render (only for variant="text") */
  lines?: number;
  /** Number of table rows to render (only for variant="table-row") */
  rows?: number;
  /** Number of columns per row (only for variant="table-row") */
  columns?: number;
  /** Additional CSS class names */
  className?: string;
}

const shimmerTransition = {
  repeat: Infinity,
  duration: 1.5,
  ease: "easeInOut" as const,
};

function SkeletonPulse({
  className = "",
  style,
}: {
  className?: string;
  style?: React.CSSProperties;
}) {
  return (
    <motion.div
      className={`skeleton-shimmer rounded ${className}`}
      style={style}
      animate={{ opacity: [0.4, 0.7, 0.4] }}
      transition={shimmerTransition}
      aria-hidden="true"
    />
  );
}

function SkeletonText({
  lines = 3,
  width,
  className = "",
}: {
  lines?: number;
  width?: string;
  className?: string;
}) {
  return (
    <div className={`space-y-2 ${className}`} style={{ width }} role="status" aria-label="Loading">
      {Array.from({ length: lines }).map((_, i) => (
        <SkeletonPulse
          key={i}
          className="h-3 rounded-md"
          style={{
            width: i === lines - 1 ? "60%" : "100%",
          }}
        />
      ))}
    </div>
  );
}

function SkeletonCircle({
  width = "48px",
  height,
  className = "",
}: {
  width?: string;
  height?: string;
  className?: string;
}) {
  return (
    <div role="status" aria-label="Loading">
      <SkeletonPulse
        className={`rounded-full ${className}`}
        style={{ width, height: height || width }}
      />
    </div>
  );
}

function SkeletonCard({
  width,
  height = "120px",
  className = "",
}: {
  width?: string;
  height?: string;
  className?: string;
}) {
  return (
    <div
      className={`rounded-lg border border-border bg-surface p-4 ${className}`}
      style={{ width, minHeight: height }}
      role="status"
      aria-label="Loading"
    >
      <div className="flex items-start gap-4">
        <SkeletonPulse className="h-12 w-12 shrink-0 rounded-lg" />
        <div className="flex-1 space-y-2">
          <SkeletonPulse className="h-3 w-24 rounded-md" />
          <SkeletonPulse className="h-6 w-16 rounded-md" />
          <SkeletonPulse className="h-2.5 w-32 rounded-md" />
        </div>
      </div>
      <div className="mt-4">
        <SkeletonPulse className="h-10 w-full rounded-md" />
      </div>
    </div>
  );
}

function SkeletonTableRow({
  rows = 5,
  columns = 6,
  className = "",
}: {
  rows?: number;
  columns?: number;
  className?: string;
}) {
  return (
    <div className={`space-y-0 ${className}`} role="status" aria-label="Loading table">
      {/* Header row */}
      <div className="flex gap-4 border-b border-border bg-surface-secondary px-4 py-3">
        {Array.from({ length: columns }).map((_, i) => (
          <SkeletonPulse
            key={`header-${i}`}
            className="h-3 rounded-md"
            style={{ width: `${100 / columns}%` }}
          />
        ))}
      </div>
      {/* Data rows */}
      {Array.from({ length: rows }).map((_, rowIdx) => (
        <div
          key={rowIdx}
          className="flex gap-4 border-b border-border/50 px-4 py-3 last:border-0"
        >
          {Array.from({ length: columns }).map((_, colIdx) => (
            <SkeletonPulse
              key={`${rowIdx}-${colIdx}`}
              className="h-3 rounded-md"
              style={{ width: `${100 / columns}%` }}
            />
          ))}
        </div>
      ))}
    </div>
  );
}

function Skeleton({
  variant = "text",
  width,
  height,
  lines,
  rows,
  columns,
  className = "",
}: SkeletonProps) {
  switch (variant) {
    case "text":
      return <SkeletonText lines={lines} width={width} className={className} />;
    case "circle":
      return <SkeletonCircle width={width} height={height} className={className} />;
    case "card":
      return <SkeletonCard width={width} height={height} className={className} />;
    case "table-row":
      return <SkeletonTableRow rows={rows} columns={columns} className={className} />;
    default:
      return <SkeletonText lines={lines} width={width} className={className} />;
  }
}

export { Skeleton, SkeletonPulse, SkeletonCard, SkeletonTableRow, SkeletonText, SkeletonCircle };
