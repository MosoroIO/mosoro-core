/* ------------------------------------------------------------------ */
/* Main application layout with sidebar + top bar                      */
/* ------------------------------------------------------------------ */

import { useState } from "react";
import { Outlet } from "react-router-dom";
import { Sidebar } from "./sidebar";
import { TopBar } from "./top-bar";
import type { ConnectionStatus } from "../../types/robot";

interface AppLayoutProps {
  connectionStatus: ConnectionStatus;
}

function AppLayout({ connectionStatus }: AppLayoutProps) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  function handleMenuToggle() {
    setIsSidebarOpen((prev) => !prev);
  }

  function handleSidebarClose() {
    setIsSidebarOpen(false);
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar isOpen={isSidebarOpen} onClose={handleSidebarClose} />

      <div className="flex flex-1 flex-col overflow-hidden">
        <TopBar
          connectionStatus={connectionStatus}
          onMenuToggle={handleMenuToggle}
        />

        <main className="flex-1 overflow-y-auto bg-surface-secondary p-4 lg:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export { AppLayout };
