/* ------------------------------------------------------------------ */
/* Robot detail page — wraps RobotDetail with route params             */
/* ------------------------------------------------------------------ */

import { useParams } from "react-router-dom";
import { RobotDetail } from "../components/robot-detail/robot-detail";
import type { FleetStatusResponse } from "../types/robot";

interface RobotDetailPageProps {
  fleetData: FleetStatusResponse | null;
}

function RobotDetailPage({ fleetData }: RobotDetailPageProps) {
  const { id } = useParams<{ id: string }>();

  if (!id) {
    return (
      <div className="card py-12 text-center">
        <p className="text-[var(--color-text-muted)]">No robot ID specified.</p>
      </div>
    );
  }

  const liveRobot = fleetData?.robots.find((r) => r.robot_id === id) || null;

  return (
    <RobotDetail robotId={id} liveRobot={liveRobot} />
  );
}

export { RobotDetailPage };
