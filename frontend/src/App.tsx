/* ------------------------------------------------------------------ */
/* Root application component with routing and providers               */
/* ------------------------------------------------------------------ */

import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
} from "react-router-dom";
import { Toaster } from "sonner";
import { AppLayout } from "./components/layout/app-layout";
import { AuthProvider, useAuthContext } from "./context/auth-context";
import { ThemeProvider } from "./context/theme-context";
import { useFleetWebSocket } from "./hooks/use-websocket";
import { CommandPalette } from "./components/command-palette/command-palette";

import { DashboardPage } from "./pages/dashboard-page";
import { RobotsPage } from "./pages/robots-page";
import { RobotDetailPage } from "./pages/robot-detail-page";
import { MapPage } from "./pages/map-page";
import { TasksPage } from "./pages/tasks-page";
import { EventsPage } from "./pages/events-page";
import { ExtensionsPage } from "./pages/extensions-page";
import { LoginPage } from "./pages/login-page";
import type { ReactNode } from "react";

/* ------------------------------------------------------------------ */
/* Protected route wrapper                                             */
/* ------------------------------------------------------------------ */

interface ProtectedRouteProps {
  children: ReactNode;
}

function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { isLoggedIn } = useAuthContext();

  if (!isLoggedIn) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}

/* ------------------------------------------------------------------ */
/* Authenticated app shell with WebSocket + layout                     */
/* ------------------------------------------------------------------ */

function AuthenticatedApp() {
  const { fleetData, connectionStatus } = useFleetWebSocket();

  return (
    <Routes>
      <Route element={<AppLayout connectionStatus={connectionStatus} />}>
        <Route
          index
          element={<DashboardPage fleetData={fleetData} />}
        />
        <Route
          path="robots"
          element={<RobotsPage fleetData={fleetData} />}
        />
        <Route
          path="robots/:id"
          element={<RobotDetailPage fleetData={fleetData} />}
        />
        <Route
          path="map"
          element={<MapPage fleetData={fleetData} />}
        />
        <Route
          path="tasks"
          element={<TasksPage fleetData={fleetData} />}
        />
        <Route path="events" element={<EventsPage />} />
        <Route path="extensions" element={<ExtensionsPage />} />
      </Route>
    </Routes>
  );
}

/* ------------------------------------------------------------------ */
/* App root                                                            */
/* ------------------------------------------------------------------ */

function App() {
  return (
    <BrowserRouter>
      <ThemeProvider>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route
              path="/*"
              element={
                <ProtectedRoute>
                  <AuthenticatedApp />
                </ProtectedRoute>
              }
            />
          </Routes>
          <CommandPalette />
          <Toaster
            position="bottom-right"
            toastOptions={{
              className:
                "bg-surface border border-border text-[var(--color-text-primary)] shadow-lg",
            }}
          />
        </AuthProvider>
      </ThemeProvider>
    </BrowserRouter>
  );
}

export default App;
