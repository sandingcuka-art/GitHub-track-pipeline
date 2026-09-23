"""Run the stats pipeline every day at 02:17 UTC."""

import time
from datetime import datetime, timedelta, timezone

from run import main as fetch_stats


def seconds_until_next_run(now: datetime | None = None) -> float:
    """Return seconds until the next 02:17 UTC run."""
    now = now or datetime.now(timezone.utc)
    next_run = now.replace(hour=2, minute=17, second=0, microsecond=0)
    if next_run <= now:
        next_run += timedelta(days=1)
    return (next_run - now).total_seconds()


def main():
    while True:
        try:
            fetch_stats()
        except Exception as error:
            # Keep the scheduler alive if Postgres or another dependency is
            # temporarily unavailable; the next daily run will retry.
            print(f"Scheduled fetch failed: {error}", flush=True)

        delay = seconds_until_next_run()
        print(f"Next scheduled fetch in {delay / 3600:.2f} hours", flush=True)
        time.sleep(delay)


if __name__ == "__main__":
    main()
