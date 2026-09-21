"""
fetch_stats.py

Step 1: prove we can pull live stats from GitHub's public API.
No database, no scheduling yet - just fetch and print.
"""

import urllib.request
import json
import os
import re

# Try to load .env if python-dotenv is available (harmless if not present)
try:
    from dotenv import load_dotenv

    # load .env from project root if present
    load_dotenv()
except Exception:
    pass

# The repos we're tracking
REPOS = [
    "pandas-dev/pandas",
    "microsoft/vscode",
    "vercel/next.js",
    "facebook/react",
    "langchain-ai/langchain",
    "Holang-1/Car-Dealership",
    "apache/airflow",
    "dbt-labs/dbt-core",
]

GITHUB_API_URL = "https://api.github.com/repos/{repo}"
GITHUB_COMMITS_API_URL = "https://api.github.com/repos/{repo}/commits?per_page=100"


def github_headers() -> dict:
    """Build GitHub API headers, including a token when one is configured."""
    headers = {"User-Agent": "track-pipeline"}
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"
    return headers


def next_page_url(link_header: str | None) -> str | None:
    """Return the next URL from GitHub's RFC 8288-style Link header."""
    if not link_header:
        return None

    match = re.search(r'<([^>]+)>;\s*rel="next"', link_header)
    return match.group(1) if match else None


def fetch_repo_stats(repo: str) -> dict:
    """Fetch current stats for a single repo from the GitHub API."""
    url = GITHUB_API_URL.format(repo=repo)
    req = urllib.request.Request(url, headers=github_headers())
    with urllib.request.urlopen(req, timeout=10) as response:
        data = json.loads(response.read().decode())

    return {
        "repo": repo,
        "stars": data["stargazers_count"],
        "forks": data["forks_count"],
        "open_issues": data["open_issues_count"],
        "watchers": data["subscribers_count"],
    }


def fetch_repo_commits(repo: str):
    """Yield every commit's SHA and timestamps for a repository, newest first."""
    url = GITHUB_COMMITS_API_URL.format(repo=repo)

    while url:
        req = urllib.request.Request(url, headers=github_headers())
        with urllib.request.urlopen(req, timeout=30) as response:
            commits = json.loads(response.read().decode())
            url = next_page_url(response.headers.get("Link"))

        for commit in commits:
            metadata = commit["commit"]
            yield {
                "repo": repo,
                "sha": commit["sha"],
                "authored_at": metadata["author"]["date"],
                "committed_at": metadata["committer"]["date"],
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
        # A bad response from one repository must not prevent the remaining
        # repositories from being collected.
        except Exception as e:
            print(f"FAILED to fetch {repo}: {e}")


if __name__ == "__main__":
    main()
