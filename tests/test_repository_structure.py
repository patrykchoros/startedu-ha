from __future__ import annotations

import json
from pathlib import Path
import unittest


class RepositoryStructureTests(unittest.TestCase):
    def test_manifest_declares_hacs_integration(self) -> None:
        manifest = json.loads(
            Path("custom_components/startedu/manifest.json").read_text(encoding="utf-8")
        )

        self.assertEqual(manifest["domain"], "startedu")
        self.assertTrue(manifest["config_flow"])
        self.assertEqual(manifest["iot_class"], "cloud_polling")
        self.assertTrue(manifest["version"])

    def test_hacs_metadata_present(self) -> None:
        hacs = json.loads(Path("hacs.json").read_text(encoding="utf-8"))

        self.assertEqual(hacs["name"], "StartEdu")
        self.assertFalse(hacs["content_in_root"])
        self.assertIn("PL", hacs["country"])
