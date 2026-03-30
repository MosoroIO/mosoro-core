/* ------------------------------------------------------------------ */
/* Map page                                                            */
/* ------------------------------------------------------------------ */

import { MapView } from "../components/map-view/map-view";
import type { FleetStatusResponse } from "../types/robot";

interface MapPageProps {
  fleetData: FleetStatusResponse | null;
}

function MapPage({ fleetData }: MapPageProps) {
  return (
    <section aria-labelledby="map-heading">
      <h2
        id="map-heading"
        className="mb-4 text-xl font-bold text-[var(--color-text-primary)]"
      >
        Fleet Map
      </h2>
      <MapView fleetData={fleetData} isLoading={!fleetData} />
    </section>
  );
}

export { MapPage };
