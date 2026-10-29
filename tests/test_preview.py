"""Cheap guardrails; verify.py checks the encoded frames after a render."""

import unittest
import re

from preview import SHOTS, VOICE, stamp


class TimelineTests(unittest.TestCase):
    def test_unique_moving_shots(self):
        self.assertEqual(len(SHOTS), 5)
        self.assertEqual(len({shot.source for shot in SHOTS}), len(SHOTS))
        self.assertEqual(sum(shot.duration for shot in SHOTS), 82)
        self.assertTrue(all(shot.start >= 0 and shot.duration >= 10 for shot in SHOTS))

    def test_subtitle_times(self):
        self.assertEqual(stamp(2.5), "0:00:02.50")
        self.assertEqual(stamp(82), "0:01:22.00")

    def test_no_direct_identifiers_or_local_paths(self):
        source_text = str((SHOTS, VOICE))
        self.assertNotRegex(source_text, r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
        self.assertNotRegex(source_text, r"\b\d{4}-\d{2}-\d{2}\b")
        self.assertTrue(all(re.fullmatch(r"[a-z0-9-]+\.mp4", shot.source) for shot in SHOTS))


if __name__ == "__main__":
    unittest.main()
