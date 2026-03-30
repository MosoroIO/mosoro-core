/* ------------------------------------------------------------------ */
/* 2D canvas-based map view showing robot positions                    */
/* ------------------------------------------------------------------ */

import { useCallback, useEffect, useRef, useState } from "react";
import type { FleetStatusResponse, RobotStatusResponse } from "../../types/robot";
import { VENDOR_COLORS, STATUS_COLORS } from "../../types/robot";

interface MapViewProps {
  fleetData: FleetStatusResponse | null;
  isLoading: boolean;
}

const CANVAS_PADDING = 40;
const ROBOT_RADIUS = 12;

interface CanvasBounds {
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
}

function computeBounds(robots: RobotStatusResponse[]): CanvasBounds {
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

  // Add some margin
  const marginX = Math.max((maxX - minX) * 0.15, 2);
  const marginY = Math.max((maxY - minY) * 0.15, 2);

  return {
    minX: minX - marginX,
    maxX: maxX + marginX,
    minY: minY - marginY,
    maxY: maxY + marginY,
  };
}

function MapView({ fleetData, isLoading }: MapViewProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [hoveredRobot, setHoveredRobot] = useState<RobotStatusResponse | null>(
    null,
  );
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });
  const [colorBy, setColorBy] = useState<"vendor" | "status">("vendor");

  const drawMap = useCallback(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container || !fleetData) return;

    const dpr = window.devicePixelRatio || 1;
    const rect = container.getBoundingClientRect();
    const width = rect.width;
    const height = rect.height;

    canvas.width = width * dpr;
    canvas.height = height * dpr;
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.scale(dpr, dpr);

    // Get theme colors from CSS variables
    const computedStyle = getComputedStyle(document.documentElement);
    const surfaceColor = computedStyle.getPropertyValue("--color-surface").trim();
    const borderColor = computedStyle.getPropertyValue("--color-border").trim();
    const textMuted = computedStyle.getPropertyValue("--color-text-muted").trim();
    const textPrimary = computedStyle.getPropertyValue("--color-text-primary").trim();

    // Clear
    ctx.fillStyle = surfaceColor || "#ffffff";
    ctx.fillRect(0, 0, width, height);

    const robots = fleetData.robots;
    const bounds = computeBounds(robots);

    const drawWidth = width - CANVAS_PADDING * 2;
    const drawHeight = height - CANVAS_PADDING * 2;
    const rangeX = bounds.maxX - bounds.minX || 1;
    const rangeY = bounds.maxY - bounds.minY || 1;

    function toCanvasX(x: number): number {
      return CANVAS_PADDING + ((x - bounds.minX) / rangeX) * drawWidth;
    }

    function toCanvasY(y: number): number {
      // Flip Y so positive is up
      return CANVAS_PADDING + (1 - (y - bounds.minY) / rangeY) * drawHeight;
    }

    // Draw grid
    ctx.strokeStyle = borderColor || "#e5e7eb";
    ctx.lineWidth = 0.5;
    ctx.setLineDash([2, 4]);

    for (let x = Math.ceil(bounds.minX); x <= Math.floor(bounds.maxX); x += Math.max(1, Math.floor(rangeX / 10))) {
      const cx = toCanvasX(x);
      ctx.beginPath();
      ctx.moveTo(cx, CANVAS_PADDING);
      ctx.lineTo(cx, height - CANVAS_PADDING);
      ctx.stroke();

      ctx.fillStyle = textMuted || "#9ca3af";
      ctx.font = "10px monospace";
      ctx.textAlign = "center";
      ctx.fillText(x.toString(), cx, height - CANVAS_PADDING + 14);
    }

    for (let y = Math.ceil(bounds.minY); y <= Math.floor(bounds.maxY); y += Math.max(1, Math.floor(rangeY / 10))) {
      const cy = toCanvasY(y);
      ctx.beginPath();
      ctx.moveTo(CANVAS_PADDING, cy);
      ctx.lineTo(width - CANVAS_PADDING, cy);
      ctx.stroke();

      ctx.fillStyle = textMuted || "#9ca3af";
      ctx.font = "10px monospace";
      ctx.textAlign = "right";
      ctx.fillText(y.toString(), CANVAS_PADDING - 6, cy + 3);
    }

    ctx.setLineDash([]);

    // Draw axes
    ctx.strokeStyle = borderColor || "#e5e7eb";
    ctx.lineWidth = 1;
    ctx.strokeRect(
      CANVAS_PADDING,
      CANVAS_PADDING,
      drawWidth,
      drawHeight,
    );

    // Draw robots
    for (const robot of robots) {
      if (!robot.position) continue;

      const cx = toCanvasX(robot.position.x);
      const cy = toCanvasY(robot.position.y);

      const color =
        colorBy === "vendor"
          ? VENDOR_COLORS[robot.vendor] || "#6b7280"
          : STATUS_COLORS[robot.status || "offline"] || "#6b7280";

      // Outer glow for online robots
      if (robot.is_online) {
        ctx.beginPath();
        ctx.arc(cx, cy, ROBOT_RADIUS + 4, 0, Math.PI * 2);
        ctx.fillStyle = `${color}30`;
        ctx.fill();
      }

      // Robot circle
      ctx.beginPath();
      ctx.arc(cx, cy, ROBOT_RADIUS, 0, Math.PI * 2);
      ctx.fillStyle = color;
      ctx.fill();

      // Border
      ctx.strokeStyle = robot.is_online ? "#ffffff" : "#666666";
      ctx.lineWidth = 2;
      ctx.stroke();

      // Heading indicator
      if (robot.position.theta !== undefined && robot.position.theta !== null) {
        const angle = (robot.position.theta * Math.PI) / 180;
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.lineTo(
          cx + Math.cos(angle) * (ROBOT_RADIUS + 6),
          cy - Math.sin(angle) * (ROBOT_RADIUS + 6),
        );
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.stroke();
      }

      // Label
      ctx.fillStyle = textPrimary || "#111827";
      ctx.font = "bold 9px sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(
        robot.robot_id.length > 10
          ? robot.robot_id.slice(0, 10) + "…"
          : robot.robot_id,
        cx,
        cy + ROBOT_RADIUS + 14,
      );
    }
  }, [fleetData, colorBy]);

  useEffect(() => {
    drawMap();

    function handleResize() {
      drawMap();
    }

    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [drawMap]);

  function handleCanvasMouseMove(e: React.MouseEvent<HTMLCanvasElement>) {
    if (!canvasRef.current || !fleetData) return;

    const rect = canvasRef.current.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    const bounds = computeBounds(fleetData.robots);
    const drawWidth = rect.width - CANVAS_PADDING * 2;
    const drawHeight = rect.height - CANVAS_PADDING * 2;
    const rangeX = bounds.maxX - bounds.minX || 1;
    const rangeY = bounds.maxY - bounds.minY || 1;

    let found: RobotStatusResponse | null = null;

    for (const robot of fleetData.robots) {
      if (!robot.position) continue;

      const cx =
        CANVAS_PADDING +
        ((robot.position.x - bounds.minX) / rangeX) * drawWidth;
      const cy =
        CANVAS_PADDING +
        (1 - (robot.position.y - bounds.minY) / rangeY) * drawHeight;

      const dist = Math.sqrt((mouseX - cx) ** 2 + (mouseY - cy) ** 2);
      if (dist <= ROBOT_RADIUS + 4) {
        found = robot;
        break;
      }
    }

    setHoveredRobot(found);
    setTooltipPos({ x: e.clientX, y: e.clientY });
  }

  function handleCanvasMouseLeave() {
    setHoveredRobot(null);
  }

  if (isLoading || !fleetData) {
    return (
      <div className="flex items-center justify-center py-20" role="status">
        <p className="text-sm text-[var(--color-text-secondary)]">
          Loading map…
        </p>
      </div>
    );
  }

  const positionedCount = fleetData.robots.filter((r) => r.position).length;

  return (
    <div className="space-y-4 animate-fade-in">
      {/* Controls */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
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
        </div>
        <p className="text-xs text-[var(--color-text-muted)]">
          {positionedCount} of {fleetData.total_robots} robots with position
          data
        </p>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-x-4 gap-y-1">
        {Object.entries(colorBy === "vendor" ? VENDOR_COLORS : STATUS_COLORS).map(
          ([key, color]) => (
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
          ),
        )}
      </div>

      {/* Canvas */}
      <div
        ref={containerRef}
        className="card relative h-[500px] p-0 overflow-hidden"
      >
        <canvas
          ref={canvasRef}
          className="h-full w-full cursor-crosshair"
          onMouseMove={handleCanvasMouseMove}
          onMouseLeave={handleCanvasMouseLeave}
          aria-label="Robot fleet map showing positions of all robots"
          role="img"
        />

        {/* Tooltip */}
        {hoveredRobot && (
          <div
            className="pointer-events-none fixed z-50 rounded-lg border border-border bg-surface p-3 shadow-lg text-sm"
            style={{
              left: tooltipPos.x + 12,
              top: tooltipPos.y + 12,
            }}
          >
            <p className="font-bold text-[var(--color-text-primary)]">
              {hoveredRobot.robot_id}
            </p>
            <p className="text-xs capitalize text-[var(--color-text-secondary)]">
              {hoveredRobot.vendor} · {hoveredRobot.status || "unknown"}
            </p>
            {hoveredRobot.battery !== null && (
              <p className="text-xs text-[var(--color-text-muted)]">
                Battery: {Math.round(hoveredRobot.battery)}%
              </p>
            )}
            {hoveredRobot.position && (
              <p className="text-xs font-mono text-[var(--color-text-muted)]">
                ({hoveredRobot.position.x.toFixed(1)},{" "}
                {hoveredRobot.position.y.toFixed(1)})
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export { MapView };
