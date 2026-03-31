/* ------------------------------------------------------------------ */
/* Summary card for fleet overview metrics                              */
/* Animated counters, sparkline charts, staggered entrance              */
/* ------------------------------------------------------------------ */

import { useEffect, useState, useRef } from "react";
import { motion, useMotionValue, useTransform, animate } from "framer-motion";
import { AreaChart, Area, ResponsiveContainer } from "recharts";
import { SkeletonPulse } from "../ui/skeleton";

interface SummaryCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: string;
  accentColor?: string;
  /** Mock trend data for sparkline — array of recent values */
  trendData?: number[];
  /** Stagger index for entrance animation */
  index?: number;
}

interface SummaryCardSkeletonProps {
  index?: number;
}

/** Animated number counter that counts up from 0 */
function AnimatedCounter({ value }: { value: number }) {
  const motionValue = useMotionValue(0);
  const rounded = useTransform(motionValue, (latest) => Math.round(latest));
  const [display, setDisplay] = useState(0);

  useEffect(() => {
    const controls = animate(motionValue, value, {
      duration: 1.2,
      ease: "easeOut",
    });

    const unsubscribe = rounded.on("change", (v) => setDisplay(v));

    return () => {
      controls.stop();
      unsubscribe();
    };
  }, [value, motionValue, rounded]);

  return <span>{display}</span>;
}

/** Sparkline mini chart */
function Sparkline({
  data,
  color,
}: {
  data: number[];
  color: string;
}) {
  const chartData = data.map((v, i) => ({ idx: i, value: v }));

  return (
    <div className="h-10 w-full mt-2">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={chartData} margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id={`sparkGrad-${color.replace(/[^a-zA-Z0-9]/g, "")}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.3} />
              <stop offset="100%" stopColor={color} stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <Area
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={1.5}
            fill={`url(#sparkGrad-${color.replace(/[^a-zA-Z0-9]/g, "")})`}
            dot={false}
            isAnimationActive={true}
            animationDuration={1000}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

const cardVariants = {
  hidden: { opacity: 0, y: 16, scale: 0.97 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    scale: 1,
    transition: {
      delay: i * 0.08,
      duration: 0.4,
      ease: [0.25, 0.46, 0.45, 0.94] as [number, number, number, number],
    },
  }),
};

function SummaryCard({
  title,
  value,
  subtitle,
  icon,
  accentColor = "var(--color-primary-500)",
  trendData,
  index = 0,
}: SummaryCardProps) {
  const isNumeric = typeof value === "number";
  const resolvedColor = useRef<string>(accentColor);

  // Resolve CSS variable to actual color for recharts
  useEffect(() => {
    if (accentColor.startsWith("var(")) {
      const varName = accentColor.replace("var(", "").replace(")", "");
      const computed = getComputedStyle(document.documentElement)
        .getPropertyValue(varName)
        .trim();
      if (computed) {
        resolvedColor.current = computed;
      }
    } else {
      resolvedColor.current = accentColor;
    }
  }, [accentColor]);

  return (
    <motion.article
      className="card flex flex-col overflow-hidden"
      variants={cardVariants}
      initial="hidden"
      animate="visible"
      custom={index}
      whileHover={{ y: -2, boxShadow: "0 8px 25px -5px rgba(0,0,0,0.1)" }}
      transition={{ type: "spring", stiffness: 300, damping: 20 }}
    >
      <div className="flex items-start gap-4">
        <div
          className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg text-xl"
          style={{ backgroundColor: `${accentColor}20`, color: accentColor }}
          aria-hidden="true"
        >
          {icon}
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-sm text-[var(--color-text-secondary)]">{title}</p>
          <p className="text-2xl font-bold text-[var(--color-text-primary)]">
            {isNumeric ? <AnimatedCounter value={value} /> : value}
          </p>
          {subtitle && (
            <p className="mt-0.5 text-xs text-[var(--color-text-muted)]">
              {subtitle}
            </p>
          )}
        </div>
      </div>

      {trendData && trendData.length > 1 && (
        <Sparkline data={trendData} color={resolvedColor.current} />
      )}
    </motion.article>
  );
}

function SummaryCardSkeleton({ index = 0 }: SummaryCardSkeletonProps) {
  return (
    <motion.div
      className="card flex flex-col overflow-hidden"
      variants={cardVariants}
      initial="hidden"
      animate="visible"
      custom={index}
    >
      <div className="flex items-start gap-4">
        <SkeletonPulse className="h-12 w-12 shrink-0 rounded-lg" />
        <div className="flex-1 space-y-2">
          <SkeletonPulse className="h-3 w-20 rounded-md" />
          <SkeletonPulse className="h-7 w-14 rounded-md" />
          <SkeletonPulse className="h-2.5 w-28 rounded-md" />
        </div>
      </div>
      <div className="mt-3">
        <SkeletonPulse className="h-10 w-full rounded-md" />
      </div>
    </motion.div>
  );
}

export { SummaryCard, SummaryCardSkeleton };
