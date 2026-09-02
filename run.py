"""
run.py

Step 1: Fetch live stats from GitHub's public API and print them.
No database, no scheduling yet.
"""

from pipeline.fetch_stats import REPOS, fetch_repo_stats


def main():
    print(f"Fetching stats for {len(REPOS)} repos...\n")

    for repo in REPOS:
        try:
            stats = fetch_repo_stats(repo)
            print(
                f"{stats['repo']:<30} "
                f"stars={stats['stars']:<8} "
                f"forks={stats['forks']:<8} "
                f"open_issues={stats['open_issues']:<6} "
                f"watchers={stats['watchers']}"
            )
        except Exception as e:
            print(f"FAILED to fetch {repo}: {e}")


if __name__ == "__main__":
    main()
