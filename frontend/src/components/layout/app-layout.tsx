/* ------------------------------------------------------------------ */
/* Main application layout with sidebar + top bar + mobile bottom nav   */
/* ------------------------------------------------------------------ */

import { useState } from "react";
import { Outlet } from "react-router-dom";
import { Sidebar } from "./sidebar";
import { TopBar } from "./top-bar";
import { BottomNav } from "./bottom-nav";
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

        {/* Add bottom padding on mobile to account for bottom nav */}
        <main className="flex-1 overflow-y-auto bg-surface-secondary p-4 pb-20 md:pb-4 lg:p-6">
          <Outlet />
        </main>
      </div>

      {/* Mobile bottom navigation — visible only on < md screens */}
      <BottomNav />
    </div>
  );
}

export { AppLayout };
