"""Fetch current stats and optionally backfill raw GitHub commit history."""

import argparse
import os
from datetime import date

import psycopg2

from fetch_stats import REPOS, fetch_repo_commits, fetch_repo_stats


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

CREATE_RAW_REPO_COMMITS_TABLE = """
CREATE TABLE IF NOT EXISTS raw_repo_commits (
    repo TEXT NOT NULL,
    sha TEXT NOT NULL,
    authored_at TIMESTAMPTZ NOT NULL,
    committed_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (repo, sha)
)
"""

UPSERT_RAW_REPO_COMMIT = """
INSERT INTO raw_repo_commits (repo, sha, authored_at, committed_at)
VALUES (%(repo)s, %(sha)s, %(authored_at)s, %(committed_at)s)
ON CONFLICT (repo, sha) DO UPDATE SET
    authored_at = EXCLUDED.authored_at,
    committed_at = EXCLUDED.committed_at
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


def ensure_raw_repo_commits_table(connection):
    """Create the idempotent raw commit history table if needed."""
    with connection.cursor() as cursor:
        cursor.execute(CREATE_RAW_REPO_COMMITS_TABLE)
    connection.commit()


def upsert_repo_commit(connection, commit: dict):
    """Insert or update one commit record using its repository SHA as the key."""
    with connection.cursor() as cursor:
        cursor.execute(UPSERT_RAW_REPO_COMMIT, commit)


def seed_commit_history(connection, repos=REPOS):
    """Backfill all available commit timestamps for each repository."""
    ensure_raw_repo_commits_table(connection)

    for repo in repos:
        try:
            commit_count = 0
            for commit in fetch_repo_commits(repo):
                upsert_repo_commit(connection, commit)
                commit_count += 1
                if commit_count % 500 == 0:
                    connection.commit()
            connection.commit()
            print(f"Seeded {commit_count} commits for {repo}")
        except Exception as error:
            connection.rollback()
            print(f"FAILED to seed commits for {repo}: {error}")


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


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--seed-commit-history",
        action="store_true",
        help="backfill all available commit timestamps for every tracked repository",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.seed_commit_history:
        connection = get_db_connection()
        try:
            seed_commit_history(connection)
        finally:
            connection.close()
    else:
        main()
