"""Unit tests for sync_skills.py."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import sync_skills


class TestSyncSkills(unittest.TestCase):
    def _write_manifest(self, root: Path, payload: dict) -> Path:
        manifest = root / "upstream-skills.json"
        manifest.write_text(json.dumps(payload), encoding="utf-8")
        return manifest

    def test_sync_creates_and_updates_skill_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = self._write_manifest(
                root,
                {
                    "skills": [
                        {
                            "name": "demo-skill",
                            "repo": "org/repo",
                            "ref": "main",
                            "files": {
                                "skills/demo/SKILL.md": ".agents/skills/demo-skill/SKILL.md"
                            },
                        }
                    ]
                },
            )
            urls: list[str] = []

            def fake_fetch(url: str) -> bytes:
                urls.append(url)
                return b"---\nname: demo-skill\n---\nhello\n"

            changed, skills = sync_skills.sync_skills(
                manifest, root=root, fetcher=fake_fetch
            )
            self.assertEqual(changed, 1)
            self.assertEqual(skills, ["demo-skill"])
            self.assertEqual(
                urls,
                ["https://raw.githubusercontent.com/org/repo/main/skills/demo/SKILL.md"],
            )
            dst = root / ".agents" / "skills" / "demo-skill" / "SKILL.md"
            self.assertEqual(dst.read_bytes(), b"---\nname: demo-skill\n---\nhello\n")

            # Re-running with identical remote content reports zero changes.
            changed_again, skills_again = sync_skills.sync_skills(
                manifest, root=root, fetcher=fake_fetch
            )
            self.assertEqual(changed_again, 0)
            self.assertEqual(skills_again, [])

    def test_check_and_dry_run_do_not_write_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = self._write_manifest(
                root,
                {
                    "skills": [
                        {
                            "name": "demo-skill",
                            "repo": "org/repo",
                            "ref": "main",
                            "files": {
                                "SKILL.md": ".agents/skills/demo-skill/SKILL.md"
                            },
                        }
                    ]
                },
            )
            changed, _ = sync_skills.sync_skills(
                manifest,
                root=root,
                check=True,
                fetcher=lambda _: b"new-content",
            )
            self.assertEqual(changed, 1)
            self.assertFalse((root / ".agents" / "skills" / "demo-skill").exists())

    def test_rejects_destination_outside_skills_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(ValueError):
                sync_skills.resolve_destination("AGENTS.md", root=root)
            with self.assertRaises(ValueError):
                sync_skills.resolve_destination(
                    ".agents/skills/../../outside.md", root=root
                )

    def test_rejects_invalid_repo_or_ref(self) -> None:
        with self.assertRaises(ValueError):
            sync_skills.build_raw_url("bad repo/slug", "main", "SKILL.md")
        with self.assertRaises(ValueError):
            sync_skills.build_raw_url("org/repo", "../evil", "SKILL.md")
        with self.assertRaises(ValueError):
            sync_skills.build_raw_url("org/repo", "main", "../secret.md")

    def test_unknown_skill_filter_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = self._write_manifest(
                root,
                {
                    "skills": [
                        {
                            "name": "demo-skill",
                            "repo": "org/repo",
                            "ref": "main",
                            "files": {
                                "SKILL.md": ".agents/skills/demo-skill/SKILL.md"
                            },
                        }
                    ]
                },
            )
            with self.assertRaises(ValueError):
                sync_skills.sync_skills(
                    manifest,
                    root=root,
                    skill_filter={"missing"},
                    fetcher=lambda _: b"",
                )


if __name__ == "__main__":
    unittest.main()
