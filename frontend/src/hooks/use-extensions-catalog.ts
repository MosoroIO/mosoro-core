/* ------------------------------------------------------------------ */
/* Hook to load and manage the extensions catalog                       */
/* Currently loads from a static JSON import; easy to swap to fetch()   */
/* ------------------------------------------------------------------ */

import { useEffect, useMemo, useState } from "react";
import type {
  Extension,
  ExtensionCatalog,
  ExtensionCategory,
  ExtensionStatus,
} from "../types/extension";

/* Static import — swap this for a fetch() call when the catalog moves
   to a remote URL. The rest of the hook stays the same. */
import catalogData from "../data/catalog.json";

interface UseExtensionsCatalogReturn {
  catalog: ExtensionCatalog | null;
  categories: ExtensionCategory[];
  extensions: Extension[];
  statuses: ExtensionStatus[];
  isLoading: boolean;
  error: string | null;
  getExtensionsByCategory: (categoryId: string) => Extension[];
  getStatus: (extensionId: string) => ExtensionStatus | undefined;
  hasNewExtensions: boolean;
}

/**
 * Provides the full extensions catalog, grouped helpers, and
 * per-extension install status.
 *
 * TODO: Replace static import with `fetch(CATALOG_URL)` when the
 * catalog is served from the API.
 */
function useExtensionsCatalog(): UseExtensionsCatalogReturn {
  const [catalog, setCatalog] = useState<ExtensionCatalog | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  /* Simulated install statuses — in production these come from the API */
  const [statuses] = useState<ExtensionStatus[]>([
    { extensionId: "locus", isInstalled: true, connectedCount: 2 },
  ]);

  useEffect(() => {
    try {
      /* When switching to fetch(), replace this with:
         const res = await fetch(CATALOG_URL);
         const data = await res.json();
         setCatalog(data as ExtensionCatalog); */
      setCatalog(catalogData as ExtensionCatalog);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load catalog");
    } finally {
      setIsLoading(false);
    }
  }, []);

  const categories = catalog?.categories ?? [];
  const extensions = catalog?.extensions ?? [];

  const getExtensionsByCategory = useMemo(() => {
    const grouped = new Map<string, Extension[]>();
    for (const ext of extensions) {
      const list = grouped.get(ext.category) ?? [];
      list.push(ext);
      grouped.set(ext.category, list);
    }
    return (categoryId: string) => grouped.get(categoryId) ?? [];
  }, [extensions]);

  function getStatus(extensionId: string): ExtensionStatus | undefined {
    return statuses.find((s) => s.extensionId === extensionId);
  }

  const hasNewExtensions = extensions.some((ext) => ext.new);

  return {
    catalog,
    categories,
    extensions,
    statuses,
    isLoading,
    error,
    getExtensionsByCategory,
    getStatus,
    hasNewExtensions,
  };
}

export { useExtensionsCatalog };
