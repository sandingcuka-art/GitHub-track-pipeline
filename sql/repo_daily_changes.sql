CREATE OR REPLACE VIEW repo_daily_changes AS
WITH snapshots_with_previous_values AS (
    SELECT
        repo,
        snapshot_date,
        stars,
        forks,
        open_issues,
        watchers,
        LAG(stars) OVER (
            PARTITION BY repo
            ORDER BY snapshot_date
        ) AS previous_stars,
        LAG(forks) OVER (
            PARTITION BY repo
            ORDER BY snapshot_date
        ) AS previous_forks
    FROM raw_repo_snapshots
)
SELECT
    repo,
    snapshot_date,
    stars,
    forks,
    open_issues,
    watchers,
    stars - previous_stars AS stars_day_over_day_change,
    forks - previous_forks AS forks_day_over_day_change,
    AVG(stars - previous_stars) OVER (
        PARTITION BY repo
        ORDER BY snapshot_date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) AS stars_growth_7_day_rolling_average
FROM snapshots_with_previous_values;
