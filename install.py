#!/usr/bin/env python3
"""Install or link ultimate-harness skills, global rules, and optional project customizations."""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SKILLS_DIR = ROOT / ".agents" / "skills"
PROJECTS_DIR = ROOT / "projects"
AGENTS_FILE = ROOT / "AGENTS.md"
RUNTIMES = ("antigravity", "claude", "codex", "gemini", "kiro")


def runtime_targets(home: Path) -> dict[str, tuple[Path, Path, Path | None]]:
    """Return (skills_dir, global_rules_path, agents_dir_or_None) for each supported runtime."""
    return {
        "antigravity": (
            home / ".gemini" / "config" / "skills",
            home / ".gemini" / "config" / "GEMINI.md",
            home / ".gemini" / "config" / "agents",
        ),
        "claude": (
            home / ".claude" / "skills",
            home / ".claude" / "CLAUDE.md",
            home / ".claude" / "agents",
        ),
        "codex": (
            home / ".agents" / "skills",
            home / ".codex" / "AGENTS.md",
            None,  # Codex requires .toml agents in ~/.codex/agents/, not .md files.
        ),
        "gemini": (
            home / ".gemini" / "skills",
            home / ".gemini" / "GEMINI.md",
            home / ".gemini" / "agents",
        ),
        "kiro": (
            home / ".kiro" / "skills",
            home / ".kiro" / "steering" / "ultimate-harness.md",
            home / ".kiro" / "agents",
        ),
    }


def is_link_or_junction(path: Path) -> bool:
    """Return True if path is a symlink or Windows NTFS junction."""
    if path.is_symlink():
        return True
    is_junction = getattr(path, "is_junction", None)
    if callable(is_junction):
        try:
            return bool(is_junction())
        except OSError:
            return False
    return False


def path_exists_or_link(path: Path) -> bool:
    """Return True if path exists, including broken symlinks or junctions."""
    return path.exists() or is_link_or_junction(path)


def remove_existing(path: Path) -> None:
    """Remove an existing file, directory, symlink, or junction."""
    if is_link_or_junction(path):
        if path.is_dir() and not path.is_symlink():
            path.rmdir()
        else:
            path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def install_entry(src: Path, dst: Path, *, is_dir: bool, mode: str, dry_run: bool, force: bool) -> None:
    """Install a single skill directory, agent file, or rules file to dst."""
    if path_exists_or_link(dst):
        if not is_link_or_junction(dst) and not force:
            print(f"[skip] {dst} (exists, not a link; pass --force to overwrite)")
            return
        if dry_run:
            action = "replace-link" if is_link_or_junction(dst) else "overwrite"
            print(f"[dry-run:{action}] {dst} <- {src}")
            return
        remove_existing(dst)

    if dry_run:
        print(f"[dry-run:{mode}] {dst} <- {src}")
        return

    dst.parent.mkdir(parents=True, exist_ok=True)

    if mode == "copy":
        if is_dir:
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)
        print(f"[copy] {dst} <- {src}")
        return

    try:
        os.symlink(src, dst, target_is_directory=is_dir)
        print(f"[link] {dst} -> {src}")
        return
    except OSError:
        pass

    if is_dir and os.name == "nt":
        res = subprocess.run(["cmd", "/c", "mklink", "/J", str(dst), str(src)], capture_output=True, text=True)
        if res.returncode == 0:
            print(f"[junction] {dst} -> {src}")
            return

    if is_dir:
        shutil.copytree(src, dst)
    else:
        shutil.copy2(src, dst)
    print(f"[copy] {dst} <- {src}")


def collect_skills(skills_dir: Path) -> list[Path]:
    """Return sorted skill folders containing SKILL.md."""
    if not skills_dir.is_dir():
        return []
    return sorted(p for p in skills_dir.iterdir() if p.is_dir() and (p / "SKILL.md").is_file())


def collect_agents(agents_dir: Path) -> list[Path]:
    """Return sorted Markdown custom agent files."""
    if not agents_dir.is_dir():
        return []
    return sorted(p for p in agents_dir.iterdir() if p.is_file() and p.suffix == ".md")


def resolve_projects(names: list[str], projects_root: Path) -> list[Path]:
    """Validate and resolve requested project directories under projects_root."""
    if not names:
        return []
    available = {p.name: p for p in sorted(projects_root.iterdir()) if p.is_dir()} if projects_root.is_dir() else {}
    if "all" in names:
        return list(available.values())
    resolved: list[Path] = []
    for name in names:
        if name not in available:
            valid = ", ".join(sorted(available)) or "(none)"
            raise ValueError(f"Unknown project {name!r}. Available: {valid}")
        resolved.append(available[name])
    return resolved


def run_install(
    *,
    root: Path = ROOT,
    home: Path | None = None,
    runtime: str = "all",
    mode: str = "link",
    dry_run: bool = False,
    force: bool = False,
    projects: list[str] | None = None,
    target: Path | None = None,
) -> int:
    """Execute global and/or project-scoped installation."""
    agents_file = root / "AGENTS.md"
    if not agents_file.is_file():
        print(f"Error: missing {agents_file}", file=sys.stderr)
        return 1

    try:
        project_dirs = resolve_projects(projects or [], root / "projects")
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    if target is not None and not project_dirs:
        print("Error: --target requires at least one --project.", file=sys.stderr)
        return 2

    if target is not None:
        target_root = target.resolve()
        for proj in project_dirs:
            print(f"=== project:{proj.name} -> {target_root} ===")
            for agent in collect_agents(proj / ".agents" / "agents"):
                install_entry(
                    agent,
                    target_root / ".agents" / "agents" / agent.name,
                    is_dir=False,
                    mode=mode,
                    dry_run=dry_run,
                    force=force,
                )
            for skill in collect_skills(proj / ".agents" / "skills"):
                install_entry(
                    skill,
                    target_root / ".agents" / "skills" / skill.name,
                    is_dir=True,
                    mode=mode,
                    dry_run=dry_run,
                    force=force,
                )
        return 0

    user_home = home or Path.home()
    skills = collect_skills(root / ".agents" / "skills")
    selected = RUNTIMES if runtime == "all" else (runtime,)
    targets = runtime_targets(user_home)

    for rt in selected:
        skills_dst_root, rules_dst, agents_dst_root = targets[rt]
        print(f"=== {rt} ===")
        install_entry(agents_file, rules_dst, is_dir=False, mode=mode, dry_run=dry_run, force=force)
        for skill in skills:
            install_entry(skill, skills_dst_root / skill.name, is_dir=True, mode=mode, dry_run=dry_run, force=force)
        for proj in project_dirs:
            for skill in collect_skills(proj / ".agents" / "skills"):
                install_entry(skill, skills_dst_root / skill.name, is_dir=True, mode=mode, dry_run=dry_run, force=force)
            for agent in collect_agents(proj / ".agents" / "agents"):
                if agents_dst_root is None:
                    print(f"[skip] {rt} requires native agent format (skipping {agent.name})")
                    continue
                install_entry(agent, agents_dst_root / agent.name, is_dir=False, mode=mode, dry_run=dry_run, force=force)

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Install ultimate-harness globally or into a project.")
    parser.add_argument("--runtime", choices=("all", *RUNTIMES), default="all", help="Target runtime (default: all)")
    parser.add_argument("--mode", choices=("link", "copy"), default="link", help="Install mode (default: link)")
    parser.add_argument("--dry-run", action="store_true", help="Print planned actions without writing")
    parser.add_argument("--force", action="store_true", help="Overwrite existing non-link files or directories")
    parser.add_argument(
        "--project",
        action="append",
        dest="projects",
        help="Also install agents/skills from projects/<name>/.agents (repeatable, or 'all')",
    )
    parser.add_argument(
        "--target",
        type=Path,
        help="Install --project agents/skills directly into <target>/.agents instead of user home",
    )
    args = parser.parse_args(argv)
    return run_install(
        runtime=args.runtime,
        mode=args.mode,
        dry_run=args.dry_run,
        force=args.force,
        projects=args.projects,
        target=args.target,
    )


if __name__ == "__main__":
    raise SystemExit(main())
