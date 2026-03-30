/* ------------------------------------------------------------------ */
/* Tasks page                                                          */
/* ------------------------------------------------------------------ */

import { TaskAssignment } from "../components/task-assignment/task-assignment";
import type { FleetStatusResponse } from "../types/robot";

interface TasksPageProps {
  fleetData: FleetStatusResponse | null;
}

function TasksPage({ fleetData }: TasksPageProps) {
  return (
    <section aria-labelledby="tasks-heading">
      <h2
        id="tasks-heading"
        className="mb-4 text-xl font-bold text-[var(--color-text-primary)]"
      >
        Task Assignment
      </h2>
      <TaskAssignment fleetData={fleetData} />
    </section>
  );
}

export { TasksPage };
