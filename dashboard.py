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
            "SELECT repo, snapshot_date, stars, forks, open_issues, watchers "
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

    st.subheader("Repository rankings")
    ranking_by = st.selectbox(
        "Rank by",
        ["Star growth rate (stars/day)", "Stars", "Forks", "Open issues", "Watchers"],
    )
    growth_period = st.selectbox("Growth period", ["7 days", "30 days", "All history"])

    ordered = visible_history.sort_values("snapshot_date")
    latest = ordered.groupby("repo", as_index=False).tail(1).set_index("repo")
    if growth_period == "All history":
        starting = ordered.groupby("repo", as_index=False).head(1).set_index("repo")
    else:
        days = int(growth_period.split()[0])
        cutoff = ordered["snapshot_date"].max() - pd.Timedelta(days=days)
        in_period = ordered[ordered["snapshot_date"] >= cutoff]
        starting = in_period.groupby("repo", as_index=False).head(1).set_index("repo")

    ranking = latest[["snapshot_date", "stars", "forks", "open_issues", "watchers"]].copy()
    common_repos = ranking.index.intersection(starting.index)
    elapsed_days = (
        latest.loc[common_repos, "snapshot_date"] - starting.loc[common_repos, "snapshot_date"]
    ).dt.total_seconds() / 86400
    ranking["Star growth (stars/day)"] = pd.NA
    growth = (
        latest.loc[common_repos, "stars"] - starting.loc[common_repos, "stars"]
    ) / elapsed_days.where(elapsed_days > 0)
    ranking.loc[common_repos, "Star growth (stars/day)"] = growth

    sort_columns = {
        "Star growth rate (stars/day)": "Star growth (stars/day)",
        "Stars": "stars",
        "Forks": "forks",
        "Open issues": "open_issues",
        "Watchers": "watchers",
    }
    ranking = ranking.sort_values(sort_columns[ranking_by], ascending=False, na_position="last")
    ranking.index.name = "Repository"
    st.caption("Growth is the change in stars divided by elapsed calendar days in the selected period.")
    st.dataframe(ranking.reset_index(), use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
