/* ------------------------------------------------------------------ */
/* Notifications bell icon + slide-out panel                           */
/* ------------------------------------------------------------------ */

import { useEffect, useRef } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Bell, X, CheckCheck, Trash2 } from "lucide-react";
import { useNotifications } from "../../context/notifications-context";
import type { NotificationRecord } from "../../types/robot";

/* ------------------------------------------------------------------ */
/* Individual notification row                                          */
/* ------------------------------------------------------------------ */
function NotificationRow({ n }: { n: NotificationRecord }) {
  const isOffline = n.event_type === "offline";
  const isError = n.event_type === "error";

  const iconColor = isOffline
    ? "text-[var(--color-warning)]"
    : isError
      ? "text-[var(--color-danger)]"
      : "text-[var(--color-text-muted)]";

  const dotColor = isOffline
    ? "bg-[var(--color-warning)]"
    : isError
      ? "bg-[var(--color-danger)]"
      : "bg-[var(--color-text-muted)]";

  return (
    <div
      className={`flex items-start gap-3 rounded-lg px-3 py-2.5 text-sm ${
        !n.read ? "bg-[var(--color-surface-secondary)]" : ""
      }`}
    >
      {/* Status dot */}
      <span
        className={`mt-1 h-2 w-2 flex-shrink-0 rounded-full ${dotColor} ${!n.read ? "ring-2 ring-current ring-offset-1 opacity-80" : "opacity-40"}`}
        aria-hidden="true"
      />
      <div className="min-w-0 flex-1">
        <p className={`font-medium leading-snug ${iconColor}`}>
          {n.event_type.toUpperCase()} — {n.robot_id}
        </p>
        <p className="text-xs text-[var(--color-text-secondary)] mt-0.5 leading-snug">
          {n.message}
        </p>
        <p className="text-[10px] text-[var(--color-text-muted)] mt-1">
          {n.vendor} · {new Date(n.timestamp * 1000).toLocaleString()}
        </p>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Notification bell button                                            */
/* ------------------------------------------------------------------ */
interface NotificationsBellProps {
  isOpen: boolean;
  onToggle: () => void;
}

function NotificationsBell({ isOpen, onToggle }: NotificationsBellProps) {
  const { unreadCount } = useNotifications();

  return (
    <button
      onClick={onToggle}
      className="btn-secondary relative !p-2"
      aria-label={`Notifications${unreadCount > 0 ? ` (${unreadCount} unread)` : ""}`}
      aria-expanded={isOpen}
    >
      <Bell className="h-5 w-5" aria-hidden="true" />
      <AnimatePresence>
        {unreadCount > 0 && (
          <motion.span
            key="badge"
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            exit={{ scale: 0 }}
            className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-[var(--color-danger)] px-1 text-[10px] font-bold text-white"
          >
            {unreadCount > 99 ? "99+" : unreadCount}
          </motion.span>
        )}
      </AnimatePresence>
    </button>
  );
}

/* ------------------------------------------------------------------ */
/* Slide-out notifications panel                                       */
/* ------------------------------------------------------------------ */
interface NotificationsPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

function NotificationsPanel({ isOpen, onClose }: NotificationsPanelProps) {
  const { notifications, markAllRead, clearAll } = useNotifications();
  const panelRef = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    if (!isOpen) return;
    function handleClick(e: MouseEvent) {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        onClose();
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [isOpen, onClose]);

  // Mark all read when panel opens
  useEffect(() => {
    if (isOpen) markAllRead();
  }, [isOpen, markAllRead]);

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          ref={panelRef}
          initial={{ opacity: 0, y: -8, scale: 0.97 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -8, scale: 0.97 }}
          transition={{ duration: 0.18 }}
          className="absolute right-0 top-14 z-50 w-80 sm:w-96 rounded-xl border border-border bg-surface shadow-xl overflow-hidden"
          role="dialog"
          aria-label="Notifications"
        >
          {/* Header */}
          <div className="flex items-center justify-between border-b border-border px-4 py-3">
            <h2 className="text-sm font-semibold text-[var(--color-text-primary)]">
              Notifications
            </h2>
            <div className="flex items-center gap-1">
              {notifications.length > 0 && (
                <>
                  <button
                    onClick={markAllRead}
                    className="btn-secondary !py-1 !px-2 text-xs gap-1"
                    title="Mark all read"
                    aria-label="Mark all notifications as read"
                  >
                    <CheckCheck className="h-3.5 w-3.5" aria-hidden="true" />
                    <span className="hidden sm:inline">Mark read</span>
                  </button>
                  <button
                    onClick={clearAll}
                    className="btn-secondary !py-1 !px-2 text-xs gap-1"
                    title="Clear all"
                    aria-label="Clear all notifications"
                  >
                    <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                  </button>
                </>
              )}
              <button
                onClick={onClose}
                className="btn-secondary !p-1"
                aria-label="Close notifications"
              >
                <X className="h-4 w-4" aria-hidden="true" />
              </button>
            </div>
          </div>

          {/* Notification list */}
          <div className="max-h-80 overflow-y-auto divide-y divide-border">
            {notifications.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-10 text-[var(--color-text-muted)]">
                <Bell className="h-8 w-8 mb-2 opacity-30" aria-hidden="true" />
                <p className="text-sm">No notifications</p>
              </div>
            ) : (
              notifications.map((n) => (
                <NotificationRow key={n.id} n={n} />
              ))
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export { NotificationsBell, NotificationsPanel };
