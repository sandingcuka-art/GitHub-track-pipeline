# GitHub Stats Pipeline

A daily data pipeline that tracks star, fork, and issue counts for a set of public GitHub repositories over time, and visualizes the trends.

## What it does

1. **Extract** — pulls daily stats (stars, forks, open issues) for a list of public repos using the GitHub API
2. **Load** — stores raw snapshots in a Postgres database (run via Docker)
3. **Transform** — SQL models calculate day-over-day deltas and rolling averages
4. **Visualize** — a simple dashboard shows growth trends across repos

## Tracked repos

- pandas-dev/pandas
- microsoft/vscode
- vercel/next.js
- facebook/react
- langchain-ai/langchain
- Holang-1/Car-Dealership

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

(Full setup instructions coming as the project is built out.)
