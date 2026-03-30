/* ------------------------------------------------------------------ */
/* Sidebar navigation component                                        */
/* ------------------------------------------------------------------ */

import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Bot,
  Map,
  ListTodo,
  TicketCheck,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
}

const NAV_ITEMS: NavItem[] = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/robots", label: "Robots", icon: Bot },
  { to: "/map", label: "Map", icon: Map },
  { to: "/tasks", label: "Tasks", icon: ListTodo },
  { to: "/events", label: "Events", icon: TicketCheck },
];

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

function Sidebar({ isOpen, onClose }: SidebarProps) {
  return (
    <>
      {/* Mobile overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      {/* Sidebar panel */}
      <aside
        className={`
          fixed inset-y-0 left-0 z-50 flex w-64 flex-col
          border-r border-border bg-surface
          transition-transform duration-200 ease-in-out
          lg:static lg:translate-x-0
          ${isOpen ? "translate-x-0" : "-translate-x-full"}
        `}
        role="navigation"
        aria-label="Main navigation"
      >
        {/* Logo / Brand */}
        <div className="flex h-16 items-center gap-3 border-b border-border px-6">
          <img
            src="/mosoro-icon.svg"
            alt="Mosoro"
            className="h-8 w-8"
          />
          <span className="text-lg font-semibold text-[var(--color-text-primary)]">
            Mosoro
          </span>
        </div>

        {/* Navigation links */}
        <nav className="flex-1 overflow-y-auto px-3 py-4">
          <ul className="space-y-1" role="list">
            {NAV_ITEMS.map((item) => {
              const Icon = item.icon;
              return (
                <li key={item.to}>
                  <NavLink
                    to={item.to}
                    end={item.to === "/"}
                    onClick={onClose}
                    className={({ isActive }) =>
                      `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors duration-150 ${
                        isActive
                          ? "bg-primary-500/10 text-primary-500"
                          : "text-[var(--color-text-secondary)] hover:bg-surface-tertiary hover:text-[var(--color-text-primary)]"
                      }`
                    }
                  >
                    <Icon className="h-5 w-5 shrink-0" aria-hidden="true" />
                    {item.label}
                  </NavLink>
                </li>
              );
            })}
          </ul>
        </nav>

        {/* Footer */}
        <div className="border-t border-border px-6 py-4">
          <p className="text-xs text-[var(--color-text-muted)]">
            Mosoro Communications Manager
          </p>
          <p className="text-xs text-[var(--color-text-muted)]">v1.0.0</p>
        </div>
      </aside>
    </>
  );
}

export { Sidebar };
