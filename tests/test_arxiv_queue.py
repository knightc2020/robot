import tempfile
import unittest
from pathlib import Path

from scripts.arxiv_queue import canonical_arxiv_id, ingest, list_candidates, mark_paper


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


if __name__ == "__main__":
    unittest.main()
