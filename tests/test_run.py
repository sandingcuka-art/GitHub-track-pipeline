import io
import unittest
from contextlib import redirect_stdout
from datetime import date
from unittest.mock import MagicMock, patch

import run


class RepoSnapshotTests(unittest.TestCase):
    def test_upsert_uses_repo_and_snapshot_date_as_conflict_key(self):
        connection = MagicMock()
        cursor = connection.cursor.return_value.__enter__.return_value
        stats = {"repo": "org/project", "stars": 12, "forks": 3, "open_issues": 4, "watchers": 5}

        run.upsert_repo_snapshot(connection, stats, snapshot_date=date(2026, 9, 21))

        statement, values = cursor.execute.call_args.args
        self.assertIn("ON CONFLICT (repo, snapshot_date) DO UPDATE", statement)
        self.assertEqual(values, {**stats, "snapshot_date": date(2026, 9, 21)})

    @patch("run.fetch_repo_stats")
    @patch("run.get_db_connection")
    def test_main_continues_after_one_repo_fails(self, mock_get_connection, mock_fetch):
        connection = MagicMock()
        mock_get_connection.return_value = connection
        repos = ["org/first", "org/broken", "org/last"]
        mock_fetch.side_effect = [
            {"repo": "org/first", "stars": 1, "forks": 2, "open_issues": 3, "watchers": 4},
            RuntimeError("GitHub unavailable"),
            {"repo": "org/last", "stars": 5, "forks": 6, "open_issues": 7, "watchers": 8},
        ]

        with patch.object(run, "REPOS", repos):
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                run.main()

        output = buffer.getvalue()
        self.assertIn("FAILED to process org/broken: GitHub unavailable", output)
        self.assertIn("org/first", output)
        self.assertIn("org/last", output)
        self.assertEqual(mock_fetch.call_count, 3)
        self.assertEqual(connection.rollback.call_count, 1)
        self.assertEqual(connection.close.call_count, 1)


if __name__ == "__main__":
    unittest.main()
