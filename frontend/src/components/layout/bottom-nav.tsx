/* ------------------------------------------------------------------ */
/* Mobile bottom navigation bar — shown on screens < 768px              */
/* ------------------------------------------------------------------ */

import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Bot,
  Map,
  ListTodo,
  TicketCheck,
  Puzzle,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

interface BottomNavItem {
  to: string;
  label: string;
  icon: LucideIcon;
}

const NAV_ITEMS: BottomNavItem[] = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/robots", label: "Robots", icon: Bot },
  { to: "/map", label: "Map", icon: Map },
  { to: "/tasks", label: "Tasks", icon: ListTodo },
  { to: "/events", label: "Events", icon: TicketCheck },
  { to: "/extensions", label: "More", icon: Puzzle },
];

function BottomNav() {
  return (
    <nav
      className="fixed inset-x-0 bottom-0 z-50 flex h-16 items-center justify-around border-t border-border bg-surface shadow-[0_-2px_10px_rgba(0,0,0,0.08)] md:hidden"
      role="navigation"
      aria-label="Mobile navigation"
    >
      {NAV_ITEMS.map((item) => {
        const Icon = item.icon;
        return (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            className={({ isActive }) =>
              `flex min-w-[44px] flex-col items-center justify-center gap-0.5 px-2 py-1.5 text-[10px] font-medium transition-colors duration-150 ${
                isActive
                  ? "text-primary-500"
                  : "text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]"
              }`
            }
          >
            <Icon className="h-5 w-5 shrink-0" aria-hidden="true" />
            <span>{item.label}</span>
          </NavLink>
        );
      })}
    </nav>
  );
}

export { BottomNav };
