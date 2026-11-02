import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import build_feed  # noqa: E402
import demo  # noqa: E402


class EstimateTime(unittest.TestCase):
    cap = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc).isoformat()

    def test_hours(self):
        self.assertEqual(build_feed.estimate_time('3h', self.cap).hour, 9)

    def test_yesterday(self):
        self.assertEqual(build_feed.estimate_time('Yesterday at 5pm', self.cap).day, 14)

    def test_month_day(self):
        self.assertEqual(build_feed.estimate_time('January 3', self.cap).day, 3)

    def test_unknown(self):
        self.assertIsNone(build_feed.estimate_time('???', self.cap))


class DemoFixture(unittest.TestCase):
    def test_fixture_is_synthetic_and_renders(self):
        import tempfile
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            out = demo.generate(Path(tmp) / 'demo')
            posts = [json.loads(l) for l in (out / 'posts.jsonl').read_text(encoding='utf-8').splitlines()]
            self.assertGreaterEqual(len(posts), 8)
            names = {p['author'] for p in posts}
            self.assertTrue(names <= {n for n, _ in demo.PEOPLE})
            for p in posts:
                self.assertTrue(p['id'].startswith('demo:'))
                self.assertNotIn('http', json.dumps(p))  # no real links, no remote images
            for svg in (out / 'media').glob('*.svg'):
                self.assertNotIn('<image', svg.read_text(encoding='utf-8'))  # flat vector art only


if __name__ == '__main__':
    unittest.main()
