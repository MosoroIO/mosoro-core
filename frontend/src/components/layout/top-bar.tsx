/* ------------------------------------------------------------------ */
/* Top bar component with connection status and dark mode toggle       */
/* ------------------------------------------------------------------ */

import { Sun, Moon, Menu } from "lucide-react";
import type { ConnectionStatus } from "../../types/robot";
import { useTheme } from "../../context/theme-context";
import { useAuthContext } from "../../context/auth-context";

interface TopBarProps {
  connectionStatus: ConnectionStatus;
  onMenuToggle: () => void;
}

function ConnectionIndicator({ status }: { status: ConnectionStatus }) {
  const colorMap: Record<ConnectionStatus, string> = {
    connected: "bg-[var(--color-success)]",
    connecting: "bg-[var(--color-warning)] animate-pulse-dot",
    disconnected: "bg-[var(--color-danger)]",
  };

  const labelMap: Record<ConnectionStatus, string> = {
    connected: "Connected",
    connecting: "Connecting…",
    disconnected: "Disconnected",
  };

  return (
    <div className="flex items-center gap-2 text-sm" role="status" aria-live="polite">
      <span
        className={`inline-block h-2.5 w-2.5 rounded-full ${colorMap[status]}`}
        aria-hidden="true"
      />
      <span className="hidden text-[var(--color-text-secondary)] sm:inline">
        {labelMap[status]}
      </span>
    </div>
  );
}

function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();

  return (
    <button
      onClick={toggleTheme}
      className="btn-secondary !p-2"
      aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
      title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
    >
      {theme === "dark" ? (
        <Sun className="h-5 w-5" aria-hidden="true" />
      ) : (
        <Moon className="h-5 w-5" aria-hidden="true" />
      )}
    </button>
  );
}

function TopBar({ connectionStatus, onMenuToggle }: TopBarProps) {
  const { isLoggedIn, logout } = useAuthContext();

  return (
    <header className="flex h-16 items-center justify-between border-b border-border bg-surface px-4 lg:px-6">
      {/* Left: hamburger menu (mobile) + logo */}
      <div className="flex items-center gap-4">
        <button
          onClick={onMenuToggle}
          className="btn-secondary !p-2 lg:hidden"
          aria-label="Toggle navigation menu"
        >
          <Menu className="h-5 w-5" aria-hidden="true" />
        </button>

        <div className="flex items-center gap-2">
          <img
            src="/mosoro-icon.svg"
            alt="Mosoro"
            className="h-7 w-7 lg:hidden"
          />
          <h1 className="text-sm font-medium text-[var(--color-text-secondary)] hidden sm:block">
            Fleet Management Dashboard
          </h1>
        </div>
      </div>

      {/* Right: status, theme, logout */}
      <div className="flex items-center gap-3">
        <ConnectionIndicator status={connectionStatus} />
        <ThemeToggle />
        {isLoggedIn && (
          <button
            onClick={logout}
            className="btn-secondary text-xs"
            aria-label="Log out"
          >
            Logout
          </button>
        )}
      </div>
    </header>
  );
}

export { TopBar };
