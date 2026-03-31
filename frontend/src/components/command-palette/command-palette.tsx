/* ------------------------------------------------------------------ */
/* Command palette — Cmd+K / Ctrl+K quick navigation                   */
/* ------------------------------------------------------------------ */

import { useEffect, useState } from "react";
import { Command } from "cmdk";
import { useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  Bot,
  Map,
  ListTodo,
  TicketCheck,
  Puzzle,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

/* ------------------------------------------------------------------ */
/* Command definitions                                                  */
/* ------------------------------------------------------------------ */

interface CommandItem {
  id: string;
  label: string;
  icon: LucideIcon;
  path: string;
  keywords?: string;
}

const COMMANDS: CommandItem[] = [
  {
    id: "dashboard",
    label: "Go to Dashboard",
    icon: LayoutDashboard,
    path: "/",
    keywords: "home overview",
  },
  {
    id: "robots",
    label: "Go to Robots",
    icon: Bot,
    path: "/robots",
    keywords: "fleet devices",
  },
  {
    id: "map",
    label: "Go to Map",
    icon: Map,
    path: "/map",
    keywords: "floor plan layout",
  },
  {
    id: "tasks",
    label: "Go to Tasks",
    icon: ListTodo,
    path: "/tasks",
    keywords: "assignments jobs",
  },
  {
    id: "events",
    label: "Go to Events",
    icon: TicketCheck,
    path: "/events",
    keywords: "logs activity",
  },
  {
    id: "extensions",
    label: "Go to Extensions",
    icon: Puzzle,
    path: "/extensions",
    keywords: "plugins adapters marketplace",
  },
];

/* ------------------------------------------------------------------ */
/* Component                                                            */
/* ------------------------------------------------------------------ */

function CommandPalette() {
  const [isOpen, setIsOpen] = useState(false);
  const navigate = useNavigate();

  /* Listen for Cmd+K / Ctrl+K */
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setIsOpen((prev) => !prev);
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, []);

  function handleSelect(path: string) {
    setIsOpen(false);
    navigate(path);
  }

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-[100] flex items-start justify-center pt-[20vh]"
      role="dialog"
      aria-modal="true"
      aria-label="Command palette"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/40 backdrop-blur-sm"
        onClick={() => setIsOpen(false)}
        aria-hidden="true"
      />

      {/* Palette */}
      <Command
        className="relative z-10 w-full max-w-lg overflow-hidden rounded-xl
                   border border-border bg-surface shadow-2xl"
        label="Command palette"
        onKeyDown={(e: React.KeyboardEvent) => {
          if (e.key === "Escape") setIsOpen(false);
        }}
      >
        <Command.Input
          placeholder="Type a command or search…"
          className="w-full border-b border-border bg-transparent px-4 py-3
                     text-sm text-[var(--color-text-primary)]
                     placeholder:text-[var(--color-text-muted)]
                     outline-none"
          autoFocus
        />

        <Command.List className="max-h-72 overflow-y-auto p-2">
          <Command.Empty className="px-4 py-6 text-center text-sm text-[var(--color-text-muted)]">
            No results found.
          </Command.Empty>

          <Command.Group
            heading="Navigation"
            className="px-2 py-1.5 text-xs font-semibold text-[var(--color-text-muted)]"
          >
            {COMMANDS.map((cmd) => {
              const Icon = cmd.icon;
              return (
                <Command.Item
                  key={cmd.id}
                  value={`${cmd.label} ${cmd.keywords ?? ""}`}
                  onSelect={() => handleSelect(cmd.path)}
                  className="flex cursor-pointer items-center gap-3 rounded-lg px-3 py-2.5
                             text-sm text-[var(--color-text-secondary)]
                             transition-colors duration-100
                             data-[selected=true]:bg-primary-500/10
                             data-[selected=true]:text-primary-500"
                >
                  <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
                  {cmd.label}
                </Command.Item>
              );
            })}
          </Command.Group>
        </Command.List>

        {/* Footer hint */}
        <div className="flex items-center justify-between border-t border-border px-4 py-2">
          <span className="text-xs text-[var(--color-text-muted)]">
            Navigate with ↑↓ · Select with ↵ · Close with Esc
          </span>
          <kbd className="rounded border border-border bg-surface-tertiary px-1.5 py-0.5 text-[10px] font-mono text-[var(--color-text-muted)]">
            ⌘K
          </kbd>
        </div>
      </Command>
    </div>
  );
}

export { CommandPalette };
