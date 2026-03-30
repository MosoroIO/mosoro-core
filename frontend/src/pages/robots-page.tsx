/* ------------------------------------------------------------------ */
/* Robots list page                                                    */
/* ------------------------------------------------------------------ */

import { RobotList } from "../components/robot-list/robot-list";
import type { FleetStatusResponse } from "../types/robot";

interface RobotsPageProps {
  fleetData: FleetStatusResponse | null;
}

function RobotsPage({ fleetData }: RobotsPageProps) {
  return (
    <section aria-labelledby="robots-heading">
      <h2
        id="robots-heading"
        className="mb-4 text-xl font-bold text-[var(--color-text-primary)]"
      >
        Robots
      </h2>
      <RobotList fleetData={fleetData} isLoading={!fleetData} />
    </section>
  );
}

export { RobotsPage };
