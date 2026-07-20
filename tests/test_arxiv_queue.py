import tempfile
import unittest
from urllib.error import HTTPError
from unittest.mock import patch
from pathlib import Path

from scripts.arxiv_queue import (
    canonical_arxiv_id,
    ingest,
    list_candidates,
    load_ledger,
    main,
    mark_paper,
    verify_published_pair,
)


SAMPLE_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/2607.15275v1</id>
    <title>RoboTTT: Context Scaling for Robot Policies</title>
    <summary>Long-context robot policies.</summary>
    <published>2026-07-16T17:59:06Z</published>
    <updated>2026-07-16T17:59:06Z</updated>
    <category term="cs.RO" />
    <arxiv:primary_category term="cs.RO" />
    <author><name>Example Author</name></author>
  </entry>
</feed>
"""

PUBLISHED_CONTENT = """---
title: \"Example\"
status: \"published\"
arxiv_id: \"2607.15275\"
---

Brief.
"""


class FakeResponse:
    def __init__(self, content: str = PUBLISHED_CONTENT):
        self.content = content

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.content.encode("utf-8")


def write_published_pair(root: Path) -> None:
    for language in ("cn", "en"):
        path = root / "src" / "content" / language / "research" / "arxiv-2607-15275.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(PUBLISHED_CONTENT, encoding="utf-8")


class ArxivQueueTest(unittest.TestCase):
    def test_canonical_id_normalizes_versions_and_urls(self):
        self.assertEqual(canonical_arxiv_id("2607.15275v2"), "2607.15275")
        self.assertEqual(
            canonical_arxiv_id("http://arxiv.org/abs/2607.15275v1"), "2607.15275"
        )

    def test_ingest_is_idempotent_and_mark_is_durable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            feed = root / "feed.xml"
            state = root / "ledger.json"
            feed.write_text(SAMPLE_FEED, encoding="utf-8")

            first = ingest(feed, state)
            second = ingest(feed, state)
            self.assertEqual(first["added_count"], 1)
            self.assertEqual(second["added_count"], 0)
            self.assertEqual(len(list_candidates(state, {"unseen"}, 30)), 1)

            mark_paper(
                state,
                "2607.15275v1",
                "published",
                96,
                "Strong real-robot results",
                "arxiv-2607-15275",
            )
            self.assertEqual(list_candidates(state, {"unseen"}, 30), [])
            published = list_candidates(state, {"published"}, 30)
            self.assertEqual(published[0]["importance_score"], 96)

    def test_verify_published_pair_requires_matching_bilingual_remote_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_published_pair(root)

            with patch("scripts.arxiv_queue.urlopen", return_value=FakeResponse()) as mock_urlopen:
                result = verify_published_pair(root, "2607.15275", "arxiv-2607-15275")

            self.assertEqual(result["arxiv_id"], "2607.15275")
            self.assertEqual(len(result["verified_paths"]), 2)
            self.assertEqual(mock_urlopen.call_count, 2)

    def test_verify_published_pair_retries_remote_propagation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_published_pair(root)
            transient_not_found = HTTPError("https://example.invalid/cn", 404, "Not Found", None, None)
            responses = [transient_not_found, FakeResponse(), FakeResponse(), FakeResponse()]

            with patch("scripts.arxiv_queue.urlopen", side_effect=responses) as mock_urlopen:
                with patch("scripts.arxiv_queue.time.sleep") as mock_sleep:
                    result = verify_published_pair(
                        root,
                        "2607.15275",
                        "arxiv-2607-15275",
                        remote_attempts=2,
                        retry_delay_seconds=0.25,
                    )

            self.assertEqual(result["remote_attempts"], 2)
            self.assertEqual(mock_urlopen.call_count, 4)
            mock_sleep.assert_called_once_with(0.25)

    def test_mark_published_requires_verification_before_ledger_write(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            feed = root / "feed.xml"
            state = root / "ledger.json"
            feed.write_text(SAMPLE_FEED, encoding="utf-8")
            ingest(feed, state)

            command = [
                "arxiv_queue.py",
                "--state",
                str(state),
                "mark",
                "--id",
                "2607.15275",
                "--status",
                "published",
                "--slug",
                "arxiv-2607-15275",
            ]
            with patch("sys.argv", command):
                with self.assertRaises(SystemExit) as error:
                    main()

            self.assertEqual(error.exception.code, 2)
            self.assertEqual(load_ledger(state)["papers"]["2607.15275"]["status"], "unseen")


if __name__ == "__main__":
    unittest.main()
