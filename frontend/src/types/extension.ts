/* ------------------------------------------------------------------ */
/* Extension catalog types — mirrors catalog.json structure             */
/* ------------------------------------------------------------------ */

export interface ExtensionConfigField {
  name: string;
  label: string;
  type: "host" | "secret" | "text";
  default_port?: number;
  path_suffix?: string;
  default?: string;
}

export interface Extension {
  id: string;
  name: string;
  category: string;
  version: string;
  tier: "free" | "premium";
  package: string;
  description: string;
  connection_type?: string;
  config_fields?: ExtensionConfigField[];
  contact_url?: string;
  new: boolean;
}

export interface ExtensionCategory {
  id: string;
  name: string;
  icon: string;
  description: string;
}

export interface ExtensionCatalog {
  version: string;
  categories: ExtensionCategory[];
  extensions: Extension[];
}

/** Runtime state for an extension (installed, connected robots, etc.) */
export interface ExtensionStatus {
  extensionId: string;
  isInstalled: boolean;
  connectedCount?: number;
}
