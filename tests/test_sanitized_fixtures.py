from __future__ import annotations

import re
import unittest
from pathlib import Path


class SanitizedFixturesTests(unittest.TestCase):
    def test_sanitized_fixtures_do_not_contain_private_identifiers(self) -> None:
        forbidden_patterns = (
            re.compile(r"@gmail\\.com", re.IGNORECASE),
            re.compile(r"Choro", re.IGNORECASE),
            re.compile(r"patryk", re.IGNORECASE),
            re.compile(r"Mateusz", re.IGNORECASE),
            re.compile(r"Urszula", re.IGNORECASE),
            re.compile(r"\\b\\d{6,}\\b"),
        )
        for fixture_path in Path("tests/fixtures").glob("startedu_*_sanitized.html"):
            content = fixture_path.read_text(encoding="utf-8")
            with self.subTest(fixture=fixture_path.name):
                for pattern in forbidden_patterns:
                    self.assertIsNone(pattern.search(content), pattern.pattern)

