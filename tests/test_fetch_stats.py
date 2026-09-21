import io
import json
import unittest
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


if __name__ == "__main__":
    unittest.main()
