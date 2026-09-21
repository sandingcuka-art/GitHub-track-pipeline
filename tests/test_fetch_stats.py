import io
import json
import unittest
import urllib.error
from contextlib import redirect_stdout
from unittest.mock import Mock, patch

import fetch_stats


class FetchRepoStatsTests(unittest.TestCase):
    @patch("fetch_stats.urllib.request.urlopen")
    @patch("fetch_stats.urllib.request.Request")
    def test_fetch_repo_stats_returns_expected_fields(self, mock_request, mock_urlopen):
        mock_response = Mock()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_response.read.return_value = json.dumps({
            "stargazers_count": 123,
            "forks_count": 45,
            "open_issues_count": 7,
            "subscribers_count": 9,
        }).encode("utf-8")
        mock_urlopen.return_value = mock_response

        result = fetch_stats.fetch_repo_stats("octocat/hello-world")

        self.assertEqual(
            result,
            {
                "repo": "octocat/hello-world",
                "stars": 123,
                "forks": 45,
                "open_issues": 7,
                "watchers": 9,
            },
        )
        mock_request.assert_called_once_with(
            "https://api.github.com/repos/octocat/hello-world",
            headers={"User-Agent": "track-pipeline"},
        )

    @patch("fetch_stats.fetch_repo_stats")
    def test_main_prints_stats_for_each_repo(self, mock_fetch_repo_stats):
        mock_fetch_repo_stats.side_effect = [
            {"repo": "alpha/repo", "stars": 10, "forks": 2, "open_issues": 3, "watchers": 1},
            {"repo": "beta/repo", "stars": 20, "forks": 4, "open_issues": 5, "watchers": 2},
        ]

        with patch.object(fetch_stats, "REPOS", ["alpha/repo", "beta/repo"]):
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                fetch_stats.main()

        output = buffer.getvalue()
        self.assertIn("Fetching stats for 2 repos", output)
        self.assertIn("alpha/repo", output)
        self.assertIn("beta/repo", output)
        self.assertIn("SUCCESS repo=alpha/repo", output)
        self.assertIn("stars=10", output)
        self.assertIn("stars=20", output)

    @patch("fetch_stats.fetch_repo_stats")
    def test_main_continues_when_one_of_eight_repos_fails(self, mock_fetch_repo_stats):
        repos = [f"org/repo-{number}" for number in range(1, 9)]
        mock_fetch_repo_stats.side_effect = [
            {"repo": repo, "stars": number, "forks": 0, "open_issues": 0, "watchers": 0}
            if number != 4
            else ValueError("invalid response")
            for number, repo in enumerate(repos, start=1)
        ]

        with patch.object(fetch_stats, "REPOS", repos):
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                fetch_stats.main()

        output = buffer.getvalue()
        self.assertIn("Fetching stats for 8 repos", output)
        self.assertIn("FAILED to fetch org/repo-4: invalid response", output)
        self.assertIn("org/repo-3", output)
        self.assertIn("org/repo-5", output)
        self.assertEqual(mock_fetch_repo_stats.call_count, 8)

    @patch("fetch_stats.urllib.request.urlopen")
    def test_fetch_repo_commits_follows_pagination(self, mock_urlopen):
        first_response = Mock()
        first_response.__enter__ = Mock(return_value=first_response)
        first_response.__exit__ = Mock(return_value=False)
        first_response.read.return_value = json.dumps([{
            "sha": "first-sha",
            "commit": {
                "author": {"date": "2020-01-01T00:00:00Z"},
                "committer": {"date": "2020-01-01T01:00:00Z"},
            },
        }]).encode("utf-8")
        first_response.headers = {
            "Link": '<https://api.github.com/repos/octocat/hello-world/commits?per_page=100&page=2>; rel="next"'
        }

        second_response = Mock()
        second_response.__enter__ = Mock(return_value=second_response)
        second_response.__exit__ = Mock(return_value=False)
        second_response.read.return_value = json.dumps([{
            "sha": "second-sha",
            "commit": {
                "author": {"date": "2020-01-02T00:00:00Z"},
                "committer": {"date": "2020-01-02T01:00:00Z"},
            },
        }]).encode("utf-8")
        second_response.headers = {}
        mock_urlopen.side_effect = [first_response, second_response]

        commits = list(fetch_stats.fetch_repo_commits("octocat/hello-world"))

        self.assertEqual([commit["sha"] for commit in commits], ["first-sha", "second-sha"])
        self.assertEqual(commits[0]["committed_at"], "2020-01-01T01:00:00Z")
        self.assertEqual(mock_urlopen.call_count, 2)

    @patch("fetch_stats.time.sleep")
    @patch("fetch_stats.urllib.request.urlopen")
    def test_fetch_repo_stats_retries_temporary_github_failure(self, mock_urlopen, mock_sleep):
        mock_response = Mock()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_response.read.return_value = json.dumps({
            "stargazers_count": 123,
            "forks_count": 45,
            "open_issues_count": 7,
            "subscribers_count": 9,
        }).encode("utf-8")
        mock_urlopen.side_effect = [urllib.error.URLError("temporary outage"), mock_response]

        result = fetch_stats.fetch_repo_stats("octocat/hello-world")

        self.assertEqual(result["stars"], 123)
        self.assertEqual(mock_urlopen.call_count, 2)
        mock_sleep.assert_called_once_with(1)

    @patch("fetch_stats.urllib.request.urlopen")
    def test_fetch_repo_stats_reports_rate_limit_reset_time(self, mock_urlopen):
        error = urllib.error.HTTPError(
            "https://api.github.com/repos/octocat/hello-world",
            403,
            "Forbidden",
            {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "1234567890"},
            None,
        )
        mock_urlopen.side_effect = error

        with self.assertRaisesRegex(
            fetch_stats.GitHubApiError,
            "GitHub API rate limit reached .*reset_at=1234567890",
        ):
            fetch_stats.fetch_repo_stats("octocat/hello-world")


if __name__ == "__main__":
    unittest.main()
