#!/usr/bin/env python3
"""Install or link ultimate-harness skills and global rules across agent runtimes."""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SKILLS_DIR = ROOT / ".agents" / "skills"
AGENTS_FILE = ROOT / "AGENTS.md"
RUNTIMES = ("antigravity", "claude", "codex", "gemini", "kiro")


def runtime_targets(home: Path) -> dict[str, tuple[Path, Path]]:
    """Return (skills_dir, global_rules_path) for each supported runtime."""
    return {
        "antigravity": (home / ".gemini" / "config" / "skills", home / ".gemini" / "config" / "GEMINI.md"),
        "claude": (home / ".claude" / "skills", home / ".claude" / "CLAUDE.md"),
        "codex": (home / ".agents" / "skills", home / ".codex" / "AGENTS.md"),
        "gemini": (home / ".gemini" / "skills", home / ".gemini" / "GEMINI.md"),
        "kiro": (home / ".kiro" / "skills", home / ".kiro" / "steering" / "ultimate-harness.md"),
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
    """Install a single skill directory or rules file to dst."""
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Install ultimate-harness globally.")
    parser.add_argument("--runtime", choices=("all", *RUNTIMES), default="all", help="Target runtime (default: all)")
    parser.add_argument("--mode", choices=("link", "copy"), default="link", help="Install mode (default: link)")
    parser.add_argument("--dry-run", action="store_true", help="Print planned actions without writing")
    parser.add_argument("--force", action="store_true", help="Overwrite existing non-link files or directories")
    args = parser.parse_args()

    if not AGENTS_FILE.is_file():
        print(f"Error: missing {AGENTS_FILE}", file=sys.stderr)
        return 1

    skills = sorted(p for p in SKILLS_DIR.iterdir() if p.is_dir() and (p / "SKILL.md").is_file()) if SKILLS_DIR.is_dir() else []
    selected = RUNTIMES if args.runtime == "all" else (args.runtime,)
    targets = runtime_targets(Path.home())

    for rt in selected:
        skills_dst_root, rules_dst = targets[rt]
        print(f"=== {rt} ===")
        install_entry(AGENTS_FILE, rules_dst, is_dir=False, mode=args.mode, dry_run=args.dry_run, force=args.force)
        for skill in skills:
            install_entry(skill, skills_dst_root / skill.name, is_dir=True, mode=args.mode, dry_run=args.dry_run, force=args.force)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
