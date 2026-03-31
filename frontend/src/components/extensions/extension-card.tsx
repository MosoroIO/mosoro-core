/* ------------------------------------------------------------------ */
/* Individual extension card — shows name, description, tier, status    */
/* ------------------------------------------------------------------ */

import { motion } from "framer-motion";
import { CheckCircle2, ExternalLink, Lock, Sparkles } from "lucide-react";
import type { Extension, ExtensionStatus } from "../../types/extension";

interface ExtensionCardProps {
  extension: Extension;
  status?: ExtensionStatus;
}

function ExtensionCard({ extension, status }: ExtensionCardProps) {
  const isInstalled = status?.isInstalled ?? false;
  const isPremium = extension.tier === "premium";
  const isNew = extension.new;

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      whileHover={{ scale: 1.01 }}
      transition={{ duration: 0.2, ease: "easeOut" }}
      className="group relative rounded-xl border border-border bg-surface p-4 shadow-sm
                 transition-shadow duration-200 hover:shadow-md"
      role="article"
      aria-label={`${extension.name} extension`}
    >
      {/* Top row: name + version + badges */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          {/* Tier icon */}
          {isPremium ? (
            <Lock
              className="h-4 w-4 shrink-0 text-[var(--color-accent-500)]"
              aria-hidden="true"
            />
          ) : isInstalled ? (
            <CheckCircle2
              className="h-4 w-4 shrink-0 text-[var(--color-success)]"
              aria-hidden="true"
            />
          ) : null}

          <h3 className="truncate text-sm font-semibold text-[var(--color-text-primary)]">
            {extension.name}
          </h3>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          {isNew && (
            <span className="badge bg-primary-100 text-primary-700 dark:bg-primary-200 dark:text-primary-800">
              <Sparkles className="mr-1 h-3 w-3" aria-hidden="true" />
              New
            </span>
          )}
          <span className="text-xs text-[var(--color-text-muted)]">
            v{extension.version}
          </span>
        </div>
      </div>

      {/* Description */}
      <p className="mt-1.5 text-sm leading-relaxed text-[var(--color-text-secondary)]">
        {extension.description}
      </p>

      {/* Footer: tier label + action */}
      <div className="mt-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <TierBadge tier={extension.tier} />
          {isInstalled && status?.connectedCount !== undefined && (
            <span className="text-xs text-[var(--color-text-muted)]">
              · {status.connectedCount} robot{status.connectedCount !== 1 ? "s" : ""} connected
            </span>
          )}
          {isInstalled && (
            <span className="text-xs font-medium text-[var(--color-success)]">
              · Installed
            </span>
          )}
        </div>

        <ActionButton
          extension={extension}
          isInstalled={isInstalled}
        />
      </div>
    </motion.div>
  );
}

/* ------------------------------------------------------------------ */
/* Sub-components                                                       */
/* ------------------------------------------------------------------ */

function TierBadge({ tier }: { tier: "free" | "premium" }) {
  if (tier === "premium") {
    return (
      <span className="badge bg-accent-100 text-accent-700 dark:bg-accent-200 dark:text-accent-800">
        Premium
      </span>
    );
  }
  return (
    <span className="badge bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400">
      Free
    </span>
  );
}

interface ActionButtonProps {
  extension: Extension;
  isInstalled: boolean;
}

function ActionButton({ extension, isInstalled }: ActionButtonProps) {
  if (isInstalled) {
    return null;
  }

  if (extension.tier === "premium") {
    const href = extension.contact_url ?? "https://mosoro.io/contact";
    return (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-1 rounded-md border border-border px-3 py-1.5
                   text-xs font-medium text-[var(--color-text-secondary)]
                   transition-colors duration-150
                   hover:bg-surface-tertiary hover:text-[var(--color-text-primary)]"
      >
        Learn More
        <ExternalLink className="h-3 w-3" aria-hidden="true" />
      </a>
    );
  }

  return (
    <button
      type="button"
      className="btn-primary px-3 py-1.5 text-xs"
      onClick={() => {
        /* TODO: Wire up install flow */
      }}
    >
      Install
    </button>
  );
}

export { ExtensionCard };
