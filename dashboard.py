"""Streamlit dashboard for daily GitHub repository star snapshots."""

import os

import pandas as pd
import psycopg2
import streamlit as st


@st.cache_data(ttl=300)
def load_star_history(database_url: str | None) -> pd.DataFrame:
    """Load all available repository star snapshots from Postgres."""
    if database_url:
        connection = psycopg2.connect(database_url)
    else:
        connection = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=os.getenv("POSTGRES_PORT", "5432"),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", "postgres"),
            dbname=os.getenv("POSTGRES_DB", "testdb"),
        )

    try:
        return pd.read_sql_query(
            "SELECT repo, snapshot_date, stars "
            "FROM raw_repo_snapshots ORDER BY snapshot_date, repo",
            connection,
            parse_dates=["snapshot_date"],
        )
    finally:
        connection.close()


def main():
    st.set_page_config(page_title="GitHub star growth", layout="wide")
    st.title("GitHub repository star growth")
    st.caption("Daily star snapshots collected by the GitHub stats pipeline")

    try:
        history = load_star_history(os.getenv("DATABASE_URL"))
    except Exception as error:
        st.error(f"Could not load snapshot data: {error}")
        st.info("Start Postgres with `docker compose up -d`, then run `python run.py` to collect snapshots.")
        return

    if history.empty:
        st.info("No snapshots found yet. Run `python run.py` to collect the first daily snapshot.")
        return

    repositories = sorted(history["repo"].unique())
    selected = st.multiselect("Repositories", repositories, default=repositories)
    visible_history = history[history["repo"].isin(selected)]

    if visible_history.empty:
        st.info("Select at least one repository to display its star history.")
        return

    chart_data = visible_history.pivot(
        index="snapshot_date", columns="repo", values="stars"
    ).sort_index()
    st.line_chart(chart_data, y_label="Stars", x_label="Snapshot date")

    latest = visible_history.sort_values("snapshot_date").groupby("repo").tail(1)
    st.subheader("Latest snapshot")
    st.dataframe(
        latest[["repo", "snapshot_date", "stars"]]
        .sort_values("stars", ascending=False)
        .reset_index(drop=True),
        use_container_width=True,
        hide_index=True,
    )


if __name__ == "__main__":
    main()
