"""Unit tests for install.py global and project-scoped installation."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import install


class TestInstall(unittest.TestCase):
    def _create_harness(self, root: Path) -> None:
        root.mkdir(parents=True, exist_ok=True)
        (root / "AGENTS.md").write_text("# Global rules\n", encoding="utf-8")
        global_skill = root / ".agents" / "skills" / "global-skill"
        global_skill.mkdir(parents=True)
        (global_skill / "SKILL.md").write_text("---\nname: global-skill\n---\n", encoding="utf-8")

        proj_agent = root / "projects" / "demo-proj" / ".agents" / "agents"
        proj_agent.mkdir(parents=True)
        (proj_agent / "fe-dev.md").write_text("---\nname: fe-dev\n---\n", encoding="utf-8")

        proj_skill = root / "projects" / "demo-proj" / ".agents" / "skills" / "proj-skill"
        proj_skill.mkdir(parents=True)
        (proj_skill / "SKILL.md").write_text("---\nname: proj-skill\n---\n", encoding="utf-8")

    def test_global_install_omits_project_assets_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "harness"
            home = Path(tmp) / "home"
            self._create_harness(root)

            rc = install.run_install(root=root, home=home, runtime="claude", mode="copy")
            self.assertEqual(rc, 0)
            self.assertTrue((home / ".claude" / "CLAUDE.md").is_file())
            self.assertTrue((home / ".claude" / "skills" / "global-skill" / "SKILL.md").is_file())
            self.assertFalse((home / ".claude" / "skills" / "proj-skill").exists())
            self.assertFalse((home / ".claude" / "agents" / "fe-dev.md").exists())
            self.assertFalse((home / ".claude" / "projects").exists())

    def test_project_install_into_user_scope_and_codex_skip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "harness"
            home = Path(tmp) / "home"
            self._create_harness(root)

            self.assertEqual(
                install.run_install(
                    root=root, home=home, runtime="claude", mode="link", projects=["demo-proj"]
                ),
                0,
            )
            self.assertTrue((home / ".claude" / "agents" / "fe-dev.md").is_symlink())
            self.assertTrue((home / ".claude" / "skills" / "proj-skill").is_symlink())

            # Codex accepts skills in ~/.agents/skills, but skips .md agents cleanly.
            self.assertEqual(
                install.run_install(
                    root=root, home=home, runtime="codex", mode="copy", projects=["demo-proj"]
                ),
                0,
            )
            self.assertTrue((home / ".agents" / "skills" / "proj-skill" / "SKILL.md").is_file())
            self.assertFalse((home / ".codex" / "agents" / "fe-dev.md").exists())

    def test_project_install_into_target_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "harness"
            target = Path(tmp) / "detective-wifey"
            target.mkdir()
            self._create_harness(root)

            rc = install.run_install(
                root=root,
                mode="link",
                projects=["demo-proj"],
                target=target,
            )
            self.assertEqual(rc, 0)
            self.assertTrue((target / ".agents" / "agents" / "fe-dev.md").is_symlink())
            self.assertTrue((target / ".agents" / "skills" / "proj-skill").is_symlink())
            self.assertFalse((target / ".agents" / "skills" / "global-skill").exists())

    def test_rejects_unknown_project_or_target_without_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "harness"
            self._create_harness(root)
            self.assertEqual(install.run_install(root=root, projects=["missing"]), 2)
            self.assertEqual(install.run_install(root=root, target=Path(tmp)), 2)


if __name__ == "__main__":
    unittest.main()
