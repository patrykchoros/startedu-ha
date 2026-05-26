from __future__ import annotations

import json
from pathlib import Path
import unittest


class RepositoryStructureTests(unittest.TestCase):
    def test_manifest_declares_hacs_integration(self) -> None:
        manifest = json.loads(
            Path("custom_components/startedu/manifest.json").read_text(encoding="utf-8")
        )

        required_keys = {
            "domain",
            "documentation",
            "issue_tracker",
            "codeowners",
            "name",
            "version",
        }
        self.assertLessEqual(required_keys, set(manifest))
        self.assertEqual(manifest["domain"], "startedu")
        self.assertTrue(manifest["config_flow"])
        self.assertEqual(manifest["iot_class"], "cloud_polling")
        self.assertEqual(
            manifest["documentation"],
            "https://github.com/patrykchoros/startedu-ha",
        )
        self.assertEqual(
            manifest["issue_tracker"],
            "https://github.com/patrykchoros/startedu-ha/issues",
        )
        self.assertEqual(manifest["codeowners"], ["@patrykchoros"])
        self.assertTrue(manifest["version"])

    def test_hacs_metadata_present(self) -> None:
        hacs = json.loads(Path("hacs.json").read_text(encoding="utf-8"))

        self.assertEqual(hacs["name"], "StartEdu")
        self.assertFalse(hacs["content_in_root"])
        self.assertIn("PL", hacs["country"])
        self.assertTrue(hacs["render_readme"])

    def test_hacs_repository_structure_has_single_integration(self) -> None:
        integrations = [
            path.name
            for path in Path("custom_components").iterdir()
            if path.is_dir()
        ]

        self.assertEqual(integrations, ["startedu"])
        self.assertTrue(Path("custom_components/startedu/manifest.json").exists())
        self.assertTrue(Path("custom_components/startedu/__init__.py").exists())

    def test_installation_docs_and_release_checklist_present(self) -> None:
        readme = Path("README.md").read_text(encoding="utf-8")
        checklist = Path("docs/release-checklist.md").read_text(encoding="utf-8")
        wiki_home = Path("docs/wiki/Home.md").read_text(encoding="utf-8")

        self.assertIn("HACS Custom Repository", readme)
        self.assertIn("https://github.com/patrykchoros/startedu-ha", readme)
        self.assertIn("Development Status", readme)
        self.assertIn("Security", readme)
        self.assertIn("release checklist", readme)
        self.assertIn("python -m unittest discover -s tests", checklist)
        self.assertIn("manifest.json` `version`", checklist)
        self.assertIn("[Release Checklist](Release-Checklist)", wiki_home)
        self.assertTrue(Path("docs/wiki/Release-Checklist.md").exists())

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


def _string_leaf_paths(
    value: object,
    prefix: tuple[str, ...] = (),
) -> set[tuple[str, ...]]:
    if isinstance(value, str):
        return {prefix}
    if not isinstance(value, dict):
        return set()

    paths: set[tuple[str, ...]] = set()
    for key, child in value.items():
        paths.update(_string_leaf_paths(child, (*prefix, key)))
    return paths
