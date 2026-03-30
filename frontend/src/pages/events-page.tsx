/* ------------------------------------------------------------------ */
/* Events page                                                         */
/* ------------------------------------------------------------------ */

import { EventsFeed } from "../components/events/events-feed";

function EventsPage() {
  return (
    <section aria-labelledby="events-heading">
      <h2
        id="events-heading"
        className="mb-4 text-xl font-bold text-[var(--color-text-primary)]"
      >
        Fleet Events
      </h2>
      <EventsFeed />
    </section>
  );
}

export { EventsPage };
