"""
fetch_stats.py

Step 1: prove we can pull live stats from GitHub's public API.
No database, no scheduling yet - just fetch and print.
"""

import urllib.request
import json

# The repos we're tracking
REPOS = [
    "pandas-dev/pandas",
    "microsoft/vscode",
    "vercel/next.js",
    "facebook/react",
    "langchain-ai/langchain",
    "Holang-1/Car-Dealership",
]

GITHUB_API_URL = "https://api.github.com/repos/{repo}"


def fetch_repo_stats(repo: str) -> dict:
    """Fetch current stats for a single repo from the GitHub API."""
    url = GITHUB_API_URL.format(repo=repo)
    req = urllib.request.Request(url, headers={"User-Agent": "track-pipeline"})
    with urllib.request.urlopen(req, timeout=10) as response:
        data = json.loads(response.read().decode())

    return {
        "repo": repo,
        "stars": data["stargazers_count"],
        "forks": data["forks_count"],
        "open_issues": data["open_issues_count"],
        "watchers": data["subscribers_count"],
    }


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
        except (urllib.error.URLError, urllib.error.HTTPError, KeyError) as e:
            print(f"FAILED to fetch {repo}: {e}")


if __name__ == "__main__":
    main()
