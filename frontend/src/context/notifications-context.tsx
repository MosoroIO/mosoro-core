/* ------------------------------------------------------------------ */
/* Notifications context — in-memory store, toast dispatch, push       */
/* ------------------------------------------------------------------ */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import { toast } from "sonner";
import type { NotificationRecord } from "../types/robot";
import type { ReactNode } from "react";

interface NotificationsContextValue {
  notifications: NotificationRecord[];
  unreadCount: number;
  addNotification: (n: NotificationRecord) => void;
  markAllRead: () => void;
  clearAll: () => void;
}

const NotificationsContext = createContext<NotificationsContextValue>({
  notifications: [],
  unreadCount: 0,
  addNotification: () => {},
  markAllRead: () => {},
  clearAll: () => {},
});

interface NotificationsProviderProps {
  children: ReactNode;
}

function NotificationsProvider({ children }: NotificationsProviderProps) {
  const [notifications, setNotifications] = useState<NotificationRecord[]>([]);
  const pushPermissionRequested = useRef(false);

  // Request browser push permission once on mount
  useEffect(() => {
    if (
      !pushPermissionRequested.current &&
      "Notification" in window &&
      Notification.permission === "default"
    ) {
      pushPermissionRequested.current = true;
      Notification.requestPermission().catch(() => {});
    }
  }, []);

  const addNotification = useCallback((n: NotificationRecord) => {
    setNotifications((prev) => {
      // Deduplicate: skip if same id already stored
      if (prev.some((existing) => existing.id === n.id)) return prev;
      const updated = [n, ...prev].slice(0, 200); // keep last 200
      return updated;
    });

    // Show sonner toast
    const toastFn = n.event_type === "offline" ? toast.warning : toast.error;
    toastFn(n.message, {
      description: `${n.vendor} · ${new Date(n.timestamp * 1000).toLocaleTimeString()}`,
      duration: 7000,
    });

    // Browser push notification (if permission granted and tab not visible)
    if (
      "Notification" in window &&
      Notification.permission === "granted" &&
      document.visibilityState === "hidden"
    ) {
      try {
        new Notification(`Mosoro Alert — ${n.event_type.toUpperCase()}`, {
          body: n.message,
          icon: "/mosoro-icon.svg",
          tag: n.id, // deduplicate by tag
        });
      } catch {
        // Ignore — some browsers restrict Notification constructor outside service workers
      }
    }
  }, []);

  const markAllRead = useCallback(() => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  }, []);

  const clearAll = useCallback(() => {
    setNotifications([]);
  }, []);

  const unreadCount = notifications.filter((n) => !n.read).length;

  return (
    <NotificationsContext.Provider
      value={{ notifications, unreadCount, addNotification, markAllRead, clearAll }}
    >
      {children}
    </NotificationsContext.Provider>
  );
}

function useNotifications() {
  return useContext(NotificationsContext);
}

export { NotificationsProvider, useNotifications };
