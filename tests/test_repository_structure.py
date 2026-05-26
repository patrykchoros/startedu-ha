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

    def test_polish_translations_cover_source_strings(self) -> None:
        source = json.loads(
            Path("custom_components/startedu/strings.json").read_text(encoding="utf-8")
        )
        polish = json.loads(
            Path("custom_components/startedu/translations/pl.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(_string_leaf_paths(source), _string_leaf_paths(polish))
        self.assertEqual(
            polish["config"]["step"]["user"]["title"],
            "Połącz StartEdu",
        )
        self.assertEqual(
            polish["event"]["cancelled_meal_prefix"],
            "ODWOŁANE",
        )


def _string_leaf_paths(value: object, prefix: tuple[str, ...] = ()) -> set[tuple[str, ...]]:
    if isinstance(value, str):
        return {prefix}
    if not isinstance(value, dict):
        return set()

    paths: set[tuple[str, ...]] = set()
    for key, child in value.items():
        paths.update(_string_leaf_paths(child, (*prefix, key)))
    return paths
