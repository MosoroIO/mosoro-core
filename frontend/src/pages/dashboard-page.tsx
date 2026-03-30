/* ------------------------------------------------------------------ */
/* Dashboard page — fleet overview                                     */
/* ------------------------------------------------------------------ */

import { FleetOverview } from "../components/fleet-overview/fleet-overview";
import type { FleetStatusResponse } from "../types/robot";

interface DashboardPageProps {
  fleetData: FleetStatusResponse | null;
}

function DashboardPage({ fleetData }: DashboardPageProps) {
  return (
    <section aria-labelledby="dashboard-heading">
      <h2
        id="dashboard-heading"
        className="mb-4 text-xl font-bold text-[var(--color-text-primary)]"
      >
        Fleet Overview
      </h2>
      <FleetOverview fleetData={fleetData} isLoading={!fleetData} />
    </section>
  );
}

export { DashboardPage };
