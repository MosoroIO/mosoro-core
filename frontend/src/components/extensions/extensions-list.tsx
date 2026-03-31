/* ------------------------------------------------------------------ */
/* Extensions list — groups extensions by category with collapsible     */
/* sections and staggered card animations                               */
/* ------------------------------------------------------------------ */

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ChevronDown } from "lucide-react";
import { ExtensionCard } from "./extension-card";
import type {
  Extension,
  ExtensionCategory,
  ExtensionStatus,
} from "../../types/extension";

/* ------------------------------------------------------------------ */
/* Animation variants                                                   */
/* ------------------------------------------------------------------ */

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.06 },
  },
};

const cardVariants = {
  hidden: { opacity: 0, y: 12 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.25, ease: "easeOut" as const },
  },
};

/* ------------------------------------------------------------------ */
/* Props                                                                */
/* ------------------------------------------------------------------ */

interface ExtensionsListProps {
  categories: ExtensionCategory[];
  getExtensionsByCategory: (categoryId: string) => Extension[];
  getStatus: (extensionId: string) => ExtensionStatus | undefined;
  searchQuery: string;
}

/* ------------------------------------------------------------------ */
/* Component                                                            */
/* ------------------------------------------------------------------ */

function ExtensionsList({
  categories,
  getExtensionsByCategory,
  getStatus,
  searchQuery,
}: ExtensionsListProps) {
  const [collapsedSections, setCollapsedSections] = useState<Set<string>>(
    new Set(),
  );

  function toggleSection(categoryId: string) {
    setCollapsedSections((prev) => {
      const next = new Set(prev);
      if (next.has(categoryId)) {
        next.delete(categoryId);
      } else {
        next.add(categoryId);
      }
      return next;
    });
  }

  const query = searchQuery.toLowerCase().trim();

  return (
    <div className="space-y-6">
      {categories.map((category) => {
        const allExtensions = getExtensionsByCategory(category.id);

        /* Filter by search query */
        const filtered = query
          ? allExtensions.filter(
              (ext) =>
                ext.name.toLowerCase().includes(query) ||
                ext.description.toLowerCase().includes(query),
            )
          : allExtensions;

        /* Hide empty categories when searching */
        if (filtered.length === 0) return null;

        const isCollapsed = collapsedSections.has(category.id);

        return (
          <section
            key={category.id}
            aria-labelledby={`category-${category.id}`}
          >
            {/* Category header — clickable to collapse */}
            <button
              type="button"
              id={`category-${category.id}`}
              onClick={() => toggleSection(category.id)}
              aria-expanded={!isCollapsed}
              aria-controls={`category-list-${category.id}`}
              className="flex w-full items-center gap-2 rounded-lg px-1 py-2
                         text-left text-sm font-semibold text-[var(--color-text-primary)]
                         transition-colors duration-150
                         hover:bg-surface-tertiary/50"
            >
              <span className="text-base" aria-hidden="true">
                {category.icon}
              </span>
              <span>{category.name}</span>
              <span className="ml-1 text-xs font-normal text-[var(--color-text-muted)]">
                ({filtered.length})
              </span>
              <ChevronDown
                className={`ml-auto h-4 w-4 text-[var(--color-text-muted)] transition-transform duration-200 ${
                  isCollapsed ? "-rotate-90" : ""
                }`}
                aria-hidden="true"
              />
            </button>

            {/* Extension cards */}
            <AnimatePresence initial={false}>
              {!isCollapsed && (
                <motion.ul
                  id={`category-list-${category.id}`}
                  role="list"
                  variants={containerVariants}
                  initial="hidden"
                  animate="visible"
                  exit={{ opacity: 0, height: 0 }}
                  className="mt-2 grid gap-3 sm:grid-cols-1 lg:grid-cols-2"
                >
                  {filtered.map((ext) => (
                    <motion.li key={ext.id} variants={cardVariants}>
                      <ExtensionCard
                        extension={ext}
                        status={getStatus(ext.id)}
                      />
                    </motion.li>
                  ))}
                </motion.ul>
              )}
            </AnimatePresence>
          </section>
        );
      })}

      {/* "What's New" section */}
      <WhatsNewSection
        extensions={categories.flatMap((c) => getExtensionsByCategory(c.id))}
      />
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* What's New section                                                   */
/* ------------------------------------------------------------------ */

function WhatsNewSection({ extensions }: { extensions: Extension[] }) {
  const newExtensions = extensions.filter((ext) => ext.new);

  return (
    <section aria-labelledby="whats-new-heading" className="mt-4">
      <h3
        id="whats-new-heading"
        className="flex items-center gap-2 px-1 py-2 text-sm font-semibold text-[var(--color-text-primary)]"
      >
        <span aria-hidden="true">🆕</span>
        What&apos;s New
      </h3>
      {newExtensions.length === 0 ? (
        <p className="px-1 text-sm text-[var(--color-text-muted)]">
          No new extensions
        </p>
      ) : (
        <ul className="mt-2 space-y-2" role="list">
          {newExtensions.map((ext) => (
            <li
              key={ext.id}
              className="text-sm text-[var(--color-text-secondary)]"
            >
              • {ext.name} — {ext.description}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export { ExtensionsList };
