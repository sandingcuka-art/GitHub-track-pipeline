"""Fetch GitHub statistics and store one daily snapshot per repository."""

import os
from datetime import date

import psycopg2

from fetch_stats import REPOS, fetch_repo_stats


CREATE_RAW_REPO_SNAPSHOTS_TABLE = """
CREATE TABLE IF NOT EXISTS raw_repo_snapshots (
    repo TEXT NOT NULL,
    snapshot_date DATE NOT NULL,
    stars INTEGER NOT NULL,
    forks INTEGER NOT NULL,
    open_issues INTEGER NOT NULL,
    watchers INTEGER NOT NULL,
    PRIMARY KEY (repo, snapshot_date)
)
"""

UPSERT_RAW_REPO_SNAPSHOT = """
INSERT INTO raw_repo_snapshots (
    repo, snapshot_date, stars, forks, open_issues, watchers
)
VALUES (%(repo)s, %(snapshot_date)s, %(stars)s, %(forks)s, %(open_issues)s, %(watchers)s)
ON CONFLICT (repo, snapshot_date) DO UPDATE SET
    stars = EXCLUDED.stars,
    forks = EXCLUDED.forks,
    open_issues = EXCLUDED.open_issues,
    watchers = EXCLUDED.watchers
"""


def get_db_connection():
    """Connect using DATABASE_URL or the local Docker Compose defaults."""
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return psycopg2.connect(database_url)

    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres"),
        dbname=os.getenv("POSTGRES_DB", "testdb"),
    )


def ensure_raw_repo_snapshots_table(connection):
    """Create the raw snapshot table and its idempotency key if needed."""
    with connection.cursor() as cursor:
        cursor.execute(CREATE_RAW_REPO_SNAPSHOTS_TABLE)
    connection.commit()


def upsert_repo_snapshot(connection, stats: dict, snapshot_date: date | None = None):
    """Insert or update a repository's statistics for one snapshot date."""
    snapshot_date = snapshot_date or date.today()
    with connection.cursor() as cursor:
        cursor.execute(
            UPSERT_RAW_REPO_SNAPSHOT,
            {**stats, "snapshot_date": snapshot_date},
        )


def main():
    print(f"Fetching stats for {len(REPOS)} repos...\n")

    connection = get_db_connection()
    try:
        ensure_raw_repo_snapshots_table(connection)

        for repo in REPOS:
            try:
                stats = fetch_repo_stats(repo)
                upsert_repo_snapshot(connection, stats)
                connection.commit()
                print(
                    f"{stats['repo']:<30} "
                    f"stars={stats['stars']:<8} "
                    f"forks={stats['forks']:<8} "
                    f"open_issues={stats['open_issues']:<6} "
                    f"watchers={stats['watchers']}"
                )
            except Exception as error:
                # A failed fetch or write must not prevent the next repo from
                # being collected. Roll back to clear a failed SQL transaction.
                connection.rollback()
                print(f"FAILED to process {repo}: {error}")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
