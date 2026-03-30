/* ------------------------------------------------------------------ */
/* Summary card for fleet overview metrics                              */
/* ------------------------------------------------------------------ */

interface SummaryCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: string;
  accentColor?: string;
}

function SummaryCard({
  title,
  value,
  subtitle,
  icon,
  accentColor = "var(--color-primary-500)",
}: SummaryCardProps) {
  return (
    <article className="card flex items-start gap-4">
      <div
        className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg text-xl"
        style={{ backgroundColor: `${accentColor}20`, color: accentColor }}
        aria-hidden="true"
      >
        {icon}
      </div>
      <div className="min-w-0">
        <p className="text-sm text-[var(--color-text-secondary)]">{title}</p>
        <p className="text-2xl font-bold text-[var(--color-text-primary)]">
          {value}
        </p>
        {subtitle && (
          <p className="mt-0.5 text-xs text-[var(--color-text-muted)]">
            {subtitle}
          </p>
        )}
      </div>
    </article>
  );
}

export { SummaryCard };
