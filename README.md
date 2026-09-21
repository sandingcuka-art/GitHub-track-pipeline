# GitHub-track-pipeline — Local development

This repository includes a `docker-compose.yml` that runs a Postgres database
for local development.

**Quick start**

- Start Postgres in the background:

```bash
docker compose up -d
```

- Stop and remove containers (keep volume):

```bash
docker compose down
```

- Remove containers and the Postgres volume (this deletes DB data):

```bash
docker compose down -v
```

**Connect to the database**

- From host (requires `psql`):

```bash
psql "host=localhost port=5432 user=postgres dbname=testdb"
```

- From inside the running container:

```bash
docker exec -it github-track-pipeline-db-1 psql -U postgres -d testdb
```

**Notes**

- The Compose file exposes Postgres on port `5432` and uses a named volume
  (`db_data`) to persist data across container recreations.
- The service currently uses `postgres:16`. Change the image tag in
  `docker-compose.yml` if you need a different Postgres version.
# GitHub Stats Pipeline

A daily data pipeline that tracks star, fork, and issue counts for a set of public GitHub repositories over time, and visualizes the trends.

## What it does

1. **Extract** — pulls daily stats (stars, forks, open issues) for a list of public repos using the GitHub API
2. **Load** — upserts raw snapshots into Postgres using `(repo, snapshot_date)` as the unique key
3. **Transform** — SQL models calculate day-over-day deltas and rolling averages
4. **Visualize** — a simple dashboard shows growth trends across repos

## Tracked repos

- pandas-dev/pandas
- microsoft/vscode
- vercel/next.js
- facebook/react
- langchain-ai/langchain
- Holang-1/Car-Dealership
- apache/airflow
- dbt-labs/dbt-core

## Tech stack

- Python (extraction script, scheduling)
- PostgreSQL (storage, via Docker)
- SQL (transformations — window functions for deltas/rolling averages)
- Streamlit (dashboard)
- Docker Compose (local environment)

## Why this project

Built to demonstrate core data engineering fundamentals: scheduled extraction, idempotent loading, SQL-based transformation, and basic visualization — using a real public API as the data source.

## Setup

```bash
docker-compose up -d
python pipeline/fetch_stats.py
```

To seed available commit history from GitHub, use a personal access token in
`.env` and run:

```bash
.venv/bin/python run.py --seed-commit-history
```

This writes commit SHAs and author/committer timestamps to `raw_repo_commits`.
The `(repo, sha)` key makes the backfill safe to rerun.

## Daily automation

`.github/workflows/daily-fetch.yml` runs the fetch-and-upsert job every day at
02:17 UTC and can also be started manually from GitHub's **Actions** tab. Add
these repository secrets before enabling it:

- `DATABASE_URL` — a connection string for a persistent Postgres database.
- `PIPELINE_GITHUB_TOKEN` — a GitHub personal access token used for API rate
  limits.

The workflow intentionally uses a persistent database URL instead of the local
Docker database, because GitHub Actions runners are temporary.

Each run writes one `SUCCESS` or `FAILED` line per repository to stdout, then
prints a success/failure summary. These logs are available in the GitHub Actions
workflow output.

(Full setup instructions coming as the project is built out.)
tracking = WTC-LMWQG2VJ
