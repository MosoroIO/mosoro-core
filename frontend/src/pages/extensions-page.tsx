/* ------------------------------------------------------------------ */
/* Extensions page — discover and install robot adapters & features     */
/* ------------------------------------------------------------------ */

import { useState } from "react";
import { motion } from "framer-motion";
import { Loader2, Search, AlertCircle } from "lucide-react";
import { ExtensionsList } from "../components/extensions/extensions-list";
import { useExtensionsCatalog } from "../hooks/use-extensions-catalog";

function ExtensionsPage() {
  const {
    categories,
    getExtensionsByCategory,
    getStatus,
    isLoading,
    error,
  } = useExtensionsCatalog();

  const [searchQuery, setSearchQuery] = useState("");

  /* ---------------------------------------------------------------- */
  /* Loading state                                                     */
  /* ---------------------------------------------------------------- */
  if (isLoading) {
    return (
      <div
        className="flex h-64 items-center justify-center"
        role="status"
        aria-label="Loading extensions"
      >
        <Loader2 className="h-6 w-6 animate-spin text-primary-500" />
        <span className="sr-only">Loading extensions…</span>
      </div>
    );
  }

  /* ---------------------------------------------------------------- */
  /* Error state                                                       */
  /* ---------------------------------------------------------------- */
  if (error) {
    return (
      <div
        className="flex h-64 flex-col items-center justify-center gap-2 text-center"
        role="alert"
      >
        <AlertCircle className="h-8 w-8 text-[var(--color-danger)]" />
        <p className="text-sm text-[var(--color-text-secondary)]">
          Failed to load extensions catalog.
        </p>
        <p className="text-xs text-[var(--color-text-muted)]">{error}</p>
      </div>
    );
  }

  /* ---------------------------------------------------------------- */
  /* Render                                                            */
  /* ---------------------------------------------------------------- */
  return (
    <motion.section
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      aria-labelledby="extensions-heading"
      className="mx-auto max-w-4xl"
    >
      {/* Header row */}
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <h2
          id="extensions-heading"
          className="text-xl font-bold text-[var(--color-text-primary)]"
        >
          Extensions
        </h2>

        {/* Search bar */}
        <div className="relative w-full sm:max-w-xs">
          <Search
            className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--color-text-muted)]"
            aria-hidden="true"
          />
          <input
            type="search"
            placeholder="Search extensions…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="input pl-9"
            aria-label="Search extensions"
          />
        </div>
      </div>

      {/* Extensions list */}
      <ExtensionsList
        categories={categories}
        getExtensionsByCategory={getExtensionsByCategory}
        getStatus={getStatus}
        searchQuery={searchQuery}
      />
    </motion.section>
  );
}

export { ExtensionsPage };
