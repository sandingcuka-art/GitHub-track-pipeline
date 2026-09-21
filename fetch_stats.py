"""
fetch_stats.py

Step 1: prove we can pull live stats from GitHub's public API.
No database, no scheduling yet - just fetch and print.
"""

import urllib.request
import urllib.error
import json
import os
import re
import time

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
MAX_GITHUB_API_ATTEMPTS = 3
RETRYABLE_HTTP_STATUS_CODES = {500, 502, 503, 504}


class GitHubApiError(RuntimeError):
    """A GitHub API failure with context suitable for pipeline logs."""


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


def fetch_github_json(url: str, attempts: int = MAX_GITHUB_API_ATTEMPTS):
    """Fetch GitHub JSON with retries for temporary network/server failures."""
    for attempt in range(1, attempts + 1):
        try:
            req = urllib.request.Request(url, headers=github_headers())
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode()), response.headers
        except urllib.error.HTTPError as error:
            headers = error.headers or {}
            rate_limited = error.code == 429 or (
                error.code == 403 and headers.get("X-RateLimit-Remaining") == "0"
            )
            if rate_limited:
                reset_at = headers.get("X-RateLimit-Reset")
                reset_message = f"; reset_at={reset_at}" if reset_at else ""
                error.close()
                raise GitHubApiError(
                    f"GitHub API rate limit reached (HTTP {error.code}){reset_message}"
                ) from error

            retryable = error.code in RETRYABLE_HTTP_STATUS_CODES
            error_message = f"GitHub API returned HTTP {error.code}"
            error.close()
        except urllib.error.URLError as error:
            retryable = True
            error_message = f"GitHub API is unavailable: {error.reason}"

        if not retryable or attempt == attempts:
            raise GitHubApiError(
                f"{error_message} after {attempt} attempt(s) for {url}"
            ) from error

        delay_seconds = 2 ** (attempt - 1)
        print(
            f"RETRY github_api attempt={attempt + 1}/{attempts} "
            f"delay_seconds={delay_seconds} error={error_message}"
        )
        time.sleep(delay_seconds)


def fetch_repo_stats(repo: str) -> dict:
    """Fetch current stats for a single repo from the GitHub API."""
    url = GITHUB_API_URL.format(repo=repo)
    data, _ = fetch_github_json(url)

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
        commits, headers = fetch_github_json(url)
        url = next_page_url(headers.get("Link"))

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
                f"SUCCESS repo={stats['repo']} "
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
