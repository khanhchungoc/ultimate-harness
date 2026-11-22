#!/usr/bin/env python3
"""Sync vendored upstream skill files declared in upstream-skills.json."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parent
DEFAULT_MANIFEST = ROOT / "upstream-skills.json"
SKILLS_ROOT = (ROOT / ".agents" / "skills").resolve()
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
REF_RE = re.compile(r"^[A-Za-z0-9_./-]+$")
REQUEST_TIMEOUT_SEC = 20

Fetcher = Callable[[str], bytes]


def _validate_rel_posix(raw_path: str, label: str) -> str:
    if not raw_path or raw_path.startswith("/") or "\\" in raw_path:
        raise ValueError(f"Invalid {label} path: {raw_path!r}")
    parts = raw_path.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise ValueError(f"Unsafe {label} path: {raw_path!r}")
    return "/".join(parts)


def resolve_destination(dst_rel: str, root: Path = ROOT) -> Path:
    """Resolve destination path and ensure it stays inside .agents/skills/."""
    clean = _validate_rel_posix(dst_rel, "destination")
    skills_root = (root / ".agents" / "skills").resolve()
    dst = (root / clean).resolve()
    if not dst.is_relative_to(skills_root) or dst == skills_root:
        raise ValueError(f"Destination escapes .agents/skills/: {dst_rel!r}")
    return dst


def build_raw_url(repo: str, ref: str, src_rel: str) -> str:
    """Build a raw.githubusercontent.com URL with strict input validation."""
    if not REPO_RE.fullmatch(repo):
        raise ValueError(f"Invalid GitHub repo slug: {repo!r}")
    if not REF_RE.fullmatch(ref) or ".." in ref.split("/"):
        raise ValueError(f"Invalid git ref: {ref!r}")
    clean_src = _validate_rel_posix(src_rel, "source")
    quoted_ref = urllib.parse.quote(ref, safe="/")
    quoted_src = urllib.parse.quote(clean_src, safe="/")
    return f"https://raw.githubusercontent.com/{repo}/{quoted_ref}/{quoted_src}"


def fetch_url(url: str) -> bytes:
    """Fetch raw file bytes over HTTPS with optional GITHUB_TOKEN auth."""
    headers = {"User-Agent": "ultimate-harness-sync-skills/1.0"}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SEC) as resp:
        return resp.read()


def load_manifest(manifest_path: Path) -> list[dict]:
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("skills"), list):
        raise ValueError("Manifest must be a JSON object with a 'skills' list.")
    entries: list[dict] = []
    for entry in data["skills"]:
        if not isinstance(entry, dict):
            raise ValueError("Each skill entry must be a JSON object.")
        for key in ("name", "repo", "ref", "files"):
            if key not in entry:
                raise ValueError(f"Skill entry missing required field {key!r}.")
        if not isinstance(entry["files"], dict) or not entry["files"]:
            raise ValueError(f"Skill {entry['name']!r} must map at least one file.")
        entries.append(entry)
    return entries


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:12]


def sync_skills(
    manifest_path: Path,
    *,
    root: Path = ROOT,
    skill_filter: set[str] | None = None,
    dry_run: bool = False,
    check: bool = False,
    fetcher: Fetcher = fetch_url,
) -> tuple[int, list[str]]:
    """Sync tracked skills. Returns (changed_count, changed_skill_names)."""
    entries = load_manifest(manifest_path)
    if skill_filter:
        known = {e["name"] for e in entries}
        unknown = sorted(skill_filter - known)
        if unknown:
            raise ValueError(f"Unknown skill(s): {', '.join(unknown)}")
        entries = [e for e in entries if e["name"] in skill_filter]

    changed_count = 0
    changed_skills: list[str] = []

    for entry in entries:
        skill_name = entry["name"]
        skill_changed = False
        for src_rel, dst_rel in entry["files"].items():
            url = build_raw_url(entry["repo"], entry["ref"], src_rel)
            dst = resolve_destination(dst_rel, root=root)
            remote_bytes = fetcher(url)
            local_bytes = dst.read_bytes() if dst.is_file() else None

            if local_bytes == remote_bytes:
                print(f"[up-to-date] {dst_rel} ({_sha256(remote_bytes)})")
                continue

            changed_count += 1
            skill_changed = True
            status = "new" if local_bytes is None else "update"

            if check or dry_run:
                mode = "check" if check else "dry-run"
                print(f"[{mode}:{status}] {dst_rel} <- {url} ({_sha256(remote_bytes)})")
                continue

            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(remote_bytes)
            print(f"[{status}] {dst_rel} <- {url} ({_sha256(remote_bytes)})")

        if skill_changed:
            changed_skills.append(skill_name)

    return changed_count, changed_skills


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Sync vendored upstream skills from upstream-skills.json."
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="Path to upstream skills manifest (default: upstream-skills.json)",
    )
    parser.add_argument(
        "--skill",
        action="append",
        dest="skills",
        help="Sync only the named skill (can be passed multiple times)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show pending updates without writing files",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 if any upstream skill file has updates (does not write)",
    )
    args = parser.parse_args(argv)

    try:
        changed, _ = sync_skills(
            args.manifest,
            skill_filter=set(args.skills) if args.skills else None,
            dry_run=args.dry_run,
            check=args.check,
        )
    except (ValueError, OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    if args.check and changed > 0:
        print(f"{changed} file(s) out of date.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
