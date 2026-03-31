/* ------------------------------------------------------------------ */
/* SVG-based interactive map view with zoom, pan, trails, tooltips      */
/* ------------------------------------------------------------------ */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { SkeletonPulse } from "../ui/skeleton";
import type { FleetStatusResponse, RobotStatusResponse } from "../../types/robot";
import { VENDOR_COLORS, STATUS_COLORS } from "../../types/robot";

interface MapViewProps {
  fleetData: FleetStatusResponse | null;
  isLoading: boolean;
}

const ROBOT_RADIUS = 10;
const MAP_PADDING = 40;
const MIN_ZOOM = 0.3;
const MAX_ZOOM = 5;
const ZOOM_SENSITIVITY = 0.001;

interface Bounds {
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
}

interface TrailPoint {
  x: number;
  y: number;
  timestamp: number;
}

function computeBounds(robots: RobotStatusResponse[]): Bounds {
  const positioned = robots.filter((r) => r.position);
  if (positioned.length === 0) {
    return { minX: -10, maxX: 10, minY: -10, maxY: 10 };
  }

  let minX = Infinity;
  let maxX = -Infinity;
  let minY = Infinity;
  let maxY = -Infinity;

  for (const robot of positioned) {
    if (!robot.position) continue;
    minX = Math.min(minX, robot.position.x);
    maxX = Math.max(maxX, robot.position.x);
    minY = Math.min(minY, robot.position.y);
    maxY = Math.max(maxY, robot.position.y);
  }

  const marginX = Math.max((maxX - minX) * 0.15, 2);
  const marginY = Math.max((maxY - minY) * 0.15, 2);

  return {
    minX: minX - marginX,
    maxX: maxX + marginX,
    minY: minY - marginY,
    maxY: maxY + marginY,
  };
}

/* ------------------------------------------------------------------ */
/* Robot marker SVG component                                           */
/* ------------------------------------------------------------------ */
function RobotMarker({
  robot,
  cx,
  cy,
  color,
  isHovered,
  onHover,
  onLeave,
  onClick,
}: {
  robot: RobotStatusResponse;
  cx: number;
  cy: number;
  color: string;
  isHovered: boolean;
  onHover: (robot: RobotStatusResponse, x: number, y: number) => void;
  onLeave: () => void;
  onClick: (robotId: string) => void;
}) {
  const isOnline = robot.is_online;
  const headingAngle = robot.position?.theta
    ? (robot.position.theta * Math.PI) / 180
    : null;

  return (
    <g
      className="cursor-pointer"
      onMouseEnter={(e) => {
        const svgRect = (e.currentTarget.ownerSVGElement as SVGSVGElement).getBoundingClientRect();
        onHover(robot, e.clientX - svgRect.left, e.clientY - svgRect.top);
      }}
      onMouseMove={(e) => {
        const svgRect = (e.currentTarget.ownerSVGElement as SVGSVGElement).getBoundingClientRect();
        onHover(robot, e.clientX - svgRect.left, e.clientY - svgRect.top);
      }}
      onMouseLeave={onLeave}
      onClick={() => onClick(robot.robot_id)}
      role="button"
      aria-label={`Robot ${robot.robot_id}: ${robot.status || "unknown"}`}
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onClick(robot.robot_id);
        }
      }}
    >
      {/* Pulse ring for online robots */}
      {isOnline && (
        <>
          <circle cx={cx} cy={cy} r={ROBOT_RADIUS + 6} fill="none" stroke={color} strokeWidth={1} opacity={0.3}>
            <animate
              attributeName="r"
              values={`${ROBOT_RADIUS + 4};${ROBOT_RADIUS + 10};${ROBOT_RADIUS + 4}`}
              dur="2s"
              repeatCount="indefinite"
            />
            <animate
              attributeName="opacity"
              values="0.3;0.1;0.3"
              dur="2s"
              repeatCount="indefinite"
            />
          </circle>
        </>
      )}

      {/* Outer glow */}
      <circle
        cx={cx}
        cy={cy}
        r={ROBOT_RADIUS + 3}
        fill={`${color}${isHovered ? "40" : "20"}`}
        style={{ transition: "fill 0.2s ease" }}
      />

      {/* Main circle */}
      <circle
        cx={cx}
        cy={cy}
        r={ROBOT_RADIUS}
        fill={color}
        stroke={isOnline ? "#ffffff" : "#666666"}
        strokeWidth={isHovered ? 2.5 : 1.5}
        style={{ transition: "stroke-width 0.2s ease, transform 0.2s ease" }}
        transform={isHovered ? `scale(1.15)` : "scale(1)"}
        transform-origin={`${cx} ${cy}`}
      />

      {/* Heading indicator */}
      {headingAngle !== null && (
        <line
          x1={cx}
          y1={cy}
          x2={cx + Math.cos(headingAngle) * (ROBOT_RADIUS + 6)}
          y2={cy - Math.sin(headingAngle) * (ROBOT_RADIUS + 6)}
          stroke={color}
          strokeWidth={2}
          strokeLinecap="round"
        />
      )}

      {/* Label */}
      <text
        x={cx}
        y={cy + ROBOT_RADIUS + 14}
        textAnchor="middle"
        className="fill-[var(--color-text-primary)]"
        fontSize={9}
        fontWeight="bold"
        fontFamily="sans-serif"
        style={{ pointerEvents: "none" }}
      >
        {robot.robot_id.length > 10
          ? robot.robot_id.slice(0, 10) + "…"
          : robot.robot_id}
      </text>
    </g>
  );
}

/* ------------------------------------------------------------------ */
/* Tooltip component                                                    */
/* ------------------------------------------------------------------ */
function MapTooltip({
  robot,
  x,
  y,
}: {
  robot: RobotStatusResponse;
  x: number;
  y: number;
}) {
  return (
    <AnimatePresence>
      <motion.div
        className="pointer-events-none absolute z-50 rounded-lg border border-border bg-surface p-3 shadow-lg text-sm"
        style={{ left: x + 16, top: y - 8 }}
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.9 }}
        transition={{ duration: 0.15 }}
      >
        <p className="font-bold text-[var(--color-text-primary)]">
          {robot.robot_id}
        </p>
        <p className="text-xs capitalize text-[var(--color-text-secondary)]">
          {robot.vendor} · {robot.status || "unknown"}
        </p>
        {robot.battery !== null && (
          <p className="text-xs text-[var(--color-text-muted)]">
            Battery: {Math.round(robot.battery)}%
          </p>
        )}
        {robot.current_task && (
          <p className="text-xs text-[var(--color-text-muted)]">
            Task: {robot.current_task.task_type}
          </p>
        )}
        {robot.position && (
          <p className="text-xs font-mono text-[var(--color-text-muted)]">
            ({robot.position.x.toFixed(1)}, {robot.position.y.toFixed(1)})
          </p>
        )}
        <p className="mt-1 text-[10px] text-[var(--color-text-muted)] italic">
          Click to view details
        </p>
      </motion.div>
    </AnimatePresence>
  );
}

/* ------------------------------------------------------------------ */
/* Map skeleton loader                                                  */
/* ------------------------------------------------------------------ */
function MapSkeleton() {
  return (
    <div className="space-y-4" role="status" aria-label="Loading map">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <SkeletonPulse className="h-4 w-16 rounded-md" />
          <SkeletonPulse className="h-9 w-36 rounded-md" />
        </div>
        <SkeletonPulse className="h-3 w-48 rounded-md" />
      </div>
      <div className="flex flex-wrap gap-x-4 gap-y-1">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="flex items-center gap-1.5">
            <SkeletonPulse className="h-3 w-3 rounded-full" />
            <SkeletonPulse className="h-3 w-14 rounded-md" />
          </div>
        ))}
      </div>
      <div className="card relative h-[500px] overflow-hidden p-0">
        <SkeletonPulse className="h-full w-full rounded-lg" />
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Main map view component                                              */
/* ------------------------------------------------------------------ */
function MapView({ fleetData, isLoading }: MapViewProps) {
  const navigate = useNavigate();
  const containerRef = useRef<HTMLDivElement>(null);
  const [colorBy, setColorBy] = useState<"vendor" | "status">("vendor");
  const [hoveredRobot, setHoveredRobot] = useState<RobotStatusResponse | null>(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });

  // Zoom and pan state
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const panStart = useRef({ x: 0, y: 0 });
  const panOffset = useRef({ x: 0, y: 0 });

  // Trail history — store last N positions per robot
  const trailsRef = useRef<Map<string, TrailPoint[]>>(new Map());

  // Container dimensions
  const [dimensions, setDimensions] = useState({ width: 800, height: 500 });

  useEffect(() => {
    function updateDimensions() {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        setDimensions({ width: rect.width, height: rect.height });
      }
    }
    updateDimensions();
    window.addEventListener("resize", updateDimensions);
    return () => window.removeEventListener("resize", updateDimensions);
  }, []);

  // Update trails when fleet data changes
  useEffect(() => {
    if (!fleetData) return;
    const now = Date.now();
    for (const robot of fleetData.robots) {
      if (!robot.position) continue;
      const trail = trailsRef.current.get(robot.robot_id) || [];
      const lastPoint = trail[trail.length - 1];
      // Only add if position changed
      if (
        !lastPoint ||
        lastPoint.x !== robot.position.x ||
        lastPoint.y !== robot.position.y
      ) {
        trail.push({ x: robot.position.x, y: robot.position.y, timestamp: now });
        // Keep last 8 positions
        if (trail.length > 8) trail.shift();
        trailsRef.current.set(robot.robot_id, trail);
      }
    }
  }, [fleetData]);

  const bounds = useMemo(() => {
    if (!fleetData) return { minX: -10, maxX: 10, minY: -10, maxY: 10 };
    return computeBounds(fleetData.robots);
  }, [fleetData]);

  const { width, height } = dimensions;
  const drawWidth = width - MAP_PADDING * 2;
  const drawHeight = height - MAP_PADDING * 2;
  const rangeX = bounds.maxX - bounds.minX || 1;
  const rangeY = bounds.maxY - bounds.minY || 1;

  const toSvgX = useCallback(
    (x: number) => MAP_PADDING + ((x - bounds.minX) / rangeX) * drawWidth,
    [bounds.minX, rangeX, drawWidth],
  );

  const toSvgY = useCallback(
    (y: number) => MAP_PADDING + (1 - (y - bounds.minY) / rangeY) * drawHeight,
    [bounds.minY, rangeY, drawHeight],
  );

  // Grid lines
  const gridLines = useMemo(() => {
    const lines: { x1: number; y1: number; x2: number; y2: number; label: string; isVertical: boolean }[] = [];
    const stepX = Math.max(1, Math.floor(rangeX / 10));
    const stepY = Math.max(1, Math.floor(rangeY / 10));

    for (let x = Math.ceil(bounds.minX); x <= Math.floor(bounds.maxX); x += stepX) {
      const sx = toSvgX(x);
      lines.push({
        x1: sx, y1: MAP_PADDING, x2: sx, y2: height - MAP_PADDING,
        label: x.toString(), isVertical: true,
      });
    }
    for (let y = Math.ceil(bounds.minY); y <= Math.floor(bounds.maxY); y += stepY) {
      const sy = toSvgY(y);
      lines.push({
        x1: MAP_PADDING, y1: sy, x2: width - MAP_PADDING, y2: sy,
        label: y.toString(), isVertical: false,
      });
    }
    return lines;
  }, [bounds, rangeX, rangeY, toSvgX, toSvgY, width, height]);

  // Zoom handler
  function handleWheel(e: React.WheelEvent) {
    e.preventDefault();
    const delta = -e.deltaY * ZOOM_SENSITIVITY;
    setZoom((prev) => Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, prev + delta * prev)));
  }

  // Pan handlers
  function handlePointerDown(e: React.PointerEvent) {
    if (e.button !== 0) return;
    setIsPanning(true);
    panStart.current = { x: e.clientX, y: e.clientY };
    panOffset.current = { ...pan };
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
  }

  function handlePointerMove(e: React.PointerEvent) {
    if (!isPanning) return;
    const dx = e.clientX - panStart.current.x;
    const dy = e.clientY - panStart.current.y;
    setPan({
      x: panOffset.current.x + dx,
      y: panOffset.current.y + dy,
    });
  }

  function handlePointerUp() {
    setIsPanning(false);
  }

  // Touch zoom (pinch)
  const lastTouchDist = useRef<number | null>(null);

  function handleTouchMove(e: React.TouchEvent) {
    if (e.touches.length === 2) {
      const dx = e.touches[0].clientX - e.touches[1].clientX;
      const dy = e.touches[0].clientY - e.touches[1].clientY;
      const dist = Math.sqrt(dx * dx + dy * dy);

      if (lastTouchDist.current !== null) {
        const delta = (dist - lastTouchDist.current) * 0.005;
        setZoom((prev) => Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, prev + delta)));
      }
      lastTouchDist.current = dist;
    }
  }

  function handleTouchEnd() {
    lastTouchDist.current = null;
  }

  function handleRobotClick(robotId: string) {
    navigate(`/robots/${encodeURIComponent(robotId)}`);
  }

  function handleRobotHover(robot: RobotStatusResponse, x: number, y: number) {
    setHoveredRobot(robot);
    setTooltipPos({ x, y });
  }

  function handleRobotLeave() {
    setHoveredRobot(null);
  }

  function handleResetView() {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  }

  if (isLoading || !fleetData) {
    return <MapSkeleton />;
  }

  const positionedCount = fleetData.robots.filter((r) => r.position).length;
  const colorMap = colorBy === "vendor" ? VENDOR_COLORS : STATUS_COLORS;

  return (
    <div className="space-y-4">
      {/* Controls */}
      <motion.div
        className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        <div className="flex items-center gap-3">
          <label className="label !mb-0">Color by:</label>
          <select
            value={colorBy}
            onChange={(e) => setColorBy(e.target.value as "vendor" | "status")}
            className="input max-w-[160px]"
            aria-label="Color robots by"
          >
            <option value="vendor">Vendor</option>
            <option value="status">Status</option>
          </select>
          <button
            onClick={handleResetView}
            className="btn-secondary text-xs"
            aria-label="Reset map view"
          >
            Reset View
          </button>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-[var(--color-text-muted)]">
            Zoom: {Math.round(zoom * 100)}%
          </span>
          <p className="text-xs text-[var(--color-text-muted)]">
            {positionedCount} of {fleetData.total_robots} robots with position data
          </p>
        </div>
      </motion.div>

      {/* Legend */}
      <motion.div
        className="flex flex-wrap gap-x-4 gap-y-1"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.3, delay: 0.1 }}
      >
        {Object.entries(colorMap).map(([key, color]) => (
          <div key={key} className="flex items-center gap-1.5 text-xs">
            <span
              className="inline-block h-3 w-3 rounded-full"
              style={{ backgroundColor: color }}
              aria-hidden="true"
            />
            <span className="capitalize text-[var(--color-text-secondary)]">
              {key}
            </span>
          </div>
        ))}
      </motion.div>

      {/* SVG Map */}
      <motion.div
        ref={containerRef}
        className="card relative h-[500px] overflow-hidden p-0"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.15 }}
        style={{ touchAction: "none" }}
      >
        <svg
          width="100%"
          height="100%"
          viewBox={`0 0 ${width} ${height}`}
          className={`h-full w-full ${isPanning ? "cursor-grabbing" : "cursor-grab"}`}
          onWheel={handleWheel}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onPointerCancel={handlePointerUp}
          onTouchMove={handleTouchMove}
          onTouchEnd={handleTouchEnd}
          aria-label="Robot fleet map showing positions of all robots"
          role="img"
        >
          {/* Background */}
          <rect
            x={0}
            y={0}
            width={width}
            height={height}
            className="fill-surface"
          />

          {/* Zoomable/pannable group */}
          <g
            transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}
            style={{ transformOrigin: `${width / 2}px ${height / 2}px` }}
          >
            {/* Grid lines */}
            {gridLines.map((line, i) => (
              <g key={i}>
                <line
                  x1={line.x1}
                  y1={line.y1}
                  x2={line.x2}
                  y2={line.y2}
                  className="stroke-[var(--color-border)]"
                  strokeWidth={0.5}
                  strokeDasharray="3 6"
                />
                {line.isVertical ? (
                  <text
                    x={line.x1}
                    y={height - MAP_PADDING + 14}
                    textAnchor="middle"
                    className="fill-[var(--color-text-muted)]"
                    fontSize={10}
                    fontFamily="monospace"
                  >
                    {line.label}
                  </text>
                ) : (
                  <text
                    x={MAP_PADDING - 6}
                    y={line.y1 + 3}
                    textAnchor="end"
                    className="fill-[var(--color-text-muted)]"
                    fontSize={10}
                    fontFamily="monospace"
                  >
                    {line.label}
                  </text>
                )}
              </g>
            ))}

            {/* Axes border */}
            <rect
              x={MAP_PADDING}
              y={MAP_PADDING}
              width={drawWidth}
              height={drawHeight}
              fill="none"
              className="stroke-[var(--color-border)]"
              strokeWidth={1}
            />

            {/* Robot trails */}
            {fleetData.robots.map((robot) => {
              if (!robot.position) return null;
              const trail = trailsRef.current.get(robot.robot_id);
              if (!trail || trail.length < 2) return null;

              const color =
                colorBy === "vendor"
                  ? VENDOR_COLORS[robot.vendor] || "#6b7280"
                  : STATUS_COLORS[robot.status || "offline"] || "#6b7280";

              return (
                <g key={`trail-${robot.robot_id}`}>
                  {trail.map((point, idx) => {
                    if (idx === trail.length - 1) return null; // Skip current position
                    const opacity = ((idx + 1) / trail.length) * 0.5;
                    const radius = 2 + (idx / trail.length) * 2;
                    return (
                      <circle
                        key={idx}
                        cx={toSvgX(point.x)}
                        cy={toSvgY(point.y)}
                        r={radius}
                        fill={color}
                        opacity={opacity}
                      />
                    );
                  })}
                  {/* Trail line connecting points */}
                  <polyline
                    points={trail
                      .map((p) => `${toSvgX(p.x)},${toSvgY(p.y)}`)
                      .join(" ")}
                    fill="none"
                    stroke={color}
                    strokeWidth={1}
                    strokeDasharray="2 3"
                    opacity={0.3}
                  />
                </g>
              );
            })}

            {/* Robot markers */}
            {fleetData.robots.map((robot) => {
              if (!robot.position) return null;

              const cx = toSvgX(robot.position.x);
              const cy = toSvgY(robot.position.y);
              const color =
                colorBy === "vendor"
                  ? VENDOR_COLORS[robot.vendor] || "#6b7280"
                  : STATUS_COLORS[robot.status || "offline"] || "#6b7280";

              return (
                <RobotMarker
                  key={robot.robot_id}
                  robot={robot}
                  cx={cx}
                  cy={cy}
                  color={color}
                  isHovered={hoveredRobot?.robot_id === robot.robot_id}
                  onHover={handleRobotHover}
                  onLeave={handleRobotLeave}
                  onClick={handleRobotClick}
                />
              );
            })}
          </g>
        </svg>

        {/* Tooltip overlay */}
        {hoveredRobot && (
          <MapTooltip robot={hoveredRobot} x={tooltipPos.x} y={tooltipPos.y} />
        )}

        {/* Zoom controls overlay */}
        <div className="absolute bottom-3 right-3 flex flex-col gap-1">
          <button
            onClick={() => setZoom((z) => Math.min(MAX_ZOOM, z * 1.3))}
            className="flex h-8 w-8 items-center justify-center rounded-md border border-border bg-surface text-sm font-bold shadow-sm hover:bg-surface-tertiary transition-colors"
            aria-label="Zoom in"
          >
            +
          </button>
          <button
            onClick={() => setZoom((z) => Math.max(MIN_ZOOM, z / 1.3))}
            className="flex h-8 w-8 items-center justify-center rounded-md border border-border bg-surface text-sm font-bold shadow-sm hover:bg-surface-tertiary transition-colors"
            aria-label="Zoom out"
          >
            −
          </button>
        </div>

        {/* Instructions hint */}
        <div className="absolute bottom-3 left-3 text-[10px] text-[var(--color-text-muted)] opacity-60">
          Scroll to zoom · Drag to pan · Click robot for details
        </div>
      </motion.div>
    </div>
  );
}

export { MapView };
