#!/usr/bin/env python3
"""Run passive security checks (built-in static checks + optional external scanners).

Built-in checks always run using Python's standard library only:
  - High-confidence secret patterns (matched values are ALWAYS redacted)
  - High-signal risky config/code patterns (disabled TLS verification, unsafe YAML,
    Python subprocess shell=True, Python pickle deserialization)

Optional external scanners are auto-detected when on PATH unless --skip-external is set:
  gitleaks, osv-scanner, npm audit, pip-audit, semgrep

Exit codes:
  0  Completed with 0 findings
  1  Completed with 1 or more findings
  2  Invalid CLI arguments or missing/unreadable target path
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

IGNORED_DIRS = frozenset({
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "dist",
    "build",
    "__pycache__",
    ".next",
    "coverage",
    ".codegraph",
    ".mypy_cache",
    ".pytest_cache",
})

PROSE_EXTENSIONS = frozenset({".md", ".markdown", ".rst", ".txt", ".adoc"})

SEVERITY_RANK = {
    "Critical": 0,
    "High": 1,
    "Medium": 2,
    "Low": 3,
    "Info": 4,
}

PLACEHOLDER_SUBSTRINGS = (
    "changeme",
    "change_me",
    "change-me",
    "placeholder",
    "example",
    "sample",
    "dummy",
    "not-a-secret",
    "not_a_secret",
    "replace_me",
    "replace-me",
    "insert_here",
    "your_api_key",
    "your-api-key",
    "your_secret",
    "your-secret",
    "your_password",
    "your-password",
    "your_token",
    "your-token",
    "redacted",
)

PLACEHOLDER_PREFIXES = (
    "your_",
    "your-",
    "my_",
    "replace_",
    "replace-",
    "insert_",
    "enter_",
    "example",
    "sample",
    "dummy",
    "fake",
    "mock",
    "test_",
    "test-",
    "testing",
    "todo",
    "fixme",
    "xxx",
    "***",
    "$",
)

# High-confidence prefixed secret rules: (rule_id, severity, message, regex, redaction_kind)
SECRET_RULES: tuple[tuple[str, str, str, re.Pattern[str], str], ...] = (
    (
        "secret-aws-access-key",
        "Critical",
        "Hardcoded AWS access key ID detected.",
        re.compile(r"\b(AKIA[0-9A-Z]{16})\b"),
        "prefix",
    ),
    (
        "secret-github-token",
        "Critical",
        "Hardcoded GitHub personal/OAuth access token detected.",
        re.compile(r"\b(gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"),
        "prefix",
    ),
    (
        "secret-stripe-live-key",
        "Critical",
        "Hardcoded Stripe live secret key detected.",
        re.compile(r"\b(sk_live_[A-Za-z0-9]{16,})\b"),
        "prefix",
    ),
    (
        "secret-slack-token",
        "High",
        "Hardcoded Slack API token detected.",
        re.compile(r"\b(xox[baprs]-[A-Za-z0-9-]{10,})\b"),
        "prefix",
    ),
    (
        "secret-private-key",
        "Critical",
        "Private key block header detected in source/config.",
        re.compile(r"(-----BEGIN [A-Z ]*PRIVATE KEY-----)"),
        "private_key",
    ),
)

GENERIC_SECRET_RE = re.compile(
    r"""(?i)\b(?:[a-z0-9_]*?(?:secret|api[_-]?key|access[_-]?token|auth[_-]?token|private[_-]?key|client[_-]?secret|password|passwd))\b\s*[:=]\s*(['"])([^'"\r\n]{8,})\1"""
)

TLS_DISABLE_RE = re.compile(
    r"""(\bverify\s*=\s*False\b|\brejectUnauthorized\s*:\s*false\b|\bInsecureSkipVerify\s*:\s*true\b|\bNODE_TLS_REJECT_UNAUTHORIZED\s*[:=]\s*['"]?0['"]?)"""
)
YAML_LOAD_RE = re.compile(r"\byaml\.load\s*\(")
SAFE_YAML_LOADER_RE = re.compile(r"\b(?:C?SafeLoader|C?BaseLoader)\b")
SHELL_TRUE_RE = re.compile(r"\bshell\s*=\s*True\b")
SUBPROCESS_CONTEXT_RE = re.compile(r"\b(?:subprocess\.\w+|Popen|check_output|check_call)\s*\(")
PICKLE_LOAD_RE = re.compile(r"\bpickle\.loads?\s*\(")

EXTERNAL_SCANNERS = ("gitleaks", "osv-scanner", "npm-audit", "pip-audit", "semgrep")


@dataclass(frozen=True)
class Finding:
    scanner: str
    rule_id: str
    severity: str
    file: str
    line: int
    message: str
    evidence: str


def positive_int(raw: str) -> int:
    try:
        value = int(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Expected an integer >= 1, got {raw!r}.") from exc
    if value < 1:
        raise argparse.ArgumentTypeError(f"Value must be >= 1, got {value}.")
    return value


def redact_secret(value: str, kind: str = "generic") -> str:
    """Return a non-reversible redacted representation of a matched secret."""
    if kind == "private_key" or value.startswith("-----BEGIN"):
        return "[REDACTED PRIVATE KEY HEADER]"
    if kind == "prefix" and len(value) > 8:
        return f"{value[:4]}****...****"
    return f"[REDACTED len={len(value)}]"


def is_placeholder_value(value: str) -> bool:
    stripped = value.strip()
    if not stripped:
        return True
    lower = stripped.lower()
    if any(token in lower for token in PLACEHOLDER_SUBSTRINGS):
        return True
    if any(lower.startswith(prefix) for prefix in PLACEHOLDER_PREFIXES):
        return True
    if ("<" in stripped and ">" in stripped) or "${" in stripped or "{{" in stripped:
        return True
    if re.fullmatch(r"\{[A-Za-z_][A-Za-z0-9_.]*\}", stripped):
        return True
    if stripped.startswith(("http://", "https://", "/", "./", "../")):
        return True
    if re.fullmatch(r"[A-Z][A-Z0-9_]{3,}", stripped):
        return True
    if set(stripped) <= set("*xX0-_."):
        return True
    return False


def is_comment_only(line: str) -> bool:
    stripped = line.lstrip()
    return stripped.startswith(("#", "//", "/*", "*"))


def normalize_relpath(path: Path, base: Path) -> str:
    try:
        rel = path.relative_to(base)
        return rel.as_posix() or path.name
    except ValueError:
        return path.as_posix()


def iter_target_files(
    target: Path, max_file_bytes: int
) -> tuple[list[tuple[Path, str]], int, int]:
    """Yield readable UTF-8 non-binary files within size bounds."""
    candidates: list[Path] = []
    if target.is_file():
        candidates.append(target)
    else:
        for dirpath, dirnames, filenames in os.walk(target):
            dirnames[:] = sorted(d for d in dirnames if d not in IGNORED_DIRS)
            for fname in sorted(filenames):
                candidates.append(Path(dirpath) / fname)

    readable: list[tuple[Path, str]] = []
    skipped_size = 0
    skipped_binary = 0
    for fpath in candidates:
        try:
            if fpath.is_symlink():
                continue
            size = fpath.stat().st_size
        except OSError:
            continue
        if size > max_file_bytes:
            skipped_size += 1
            continue
        try:
            raw = fpath.read_bytes()
        except OSError:
            continue
        if b"\x00" in raw[:8192]:
            skipped_binary += 1
            continue
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            skipped_binary += 1
            continue
        readable.append((fpath, text))
    return readable, skipped_size, skipped_binary


def scan_builtin(target: Path, max_file_kb: int) -> tuple[list[Finding], dict[str, int]]:
    base = target.parent if target.is_file() else target
    max_file_bytes = max_file_kb * 1024
    files, skipped_size, skipped_binary = iter_target_files(target, max_file_bytes)
    findings: list[Finding] = []

    for fpath, content in files:
        rel = normalize_relpath(fpath, base)
        lines = content.splitlines()
        is_prose = fpath.suffix.lower() in PROSE_EXTENSIONS

        for idx, line in enumerate(lines):
            lineno = idx + 1
            matched_specific_secret = False

            for rule_id, severity, message, pattern, redact_kind in SECRET_RULES:
                for match in pattern.finditer(line):
                    matched_specific_secret = True
                    findings.append(
                        Finding(
                            scanner="builtin-static",
                            rule_id=rule_id,
                            severity=severity,
                            file=rel,
                            line=lineno,
                            message=message,
                            evidence=redact_secret(match.group(1), redact_kind),
                        )
                    )

            if not matched_specific_secret:
                for match in GENERIC_SECRET_RE.finditer(line):
                    literal = match.group(2)
                    if is_placeholder_value(literal):
                        continue
                    findings.append(
                        Finding(
                            scanner="builtin-static",
                            rule_id="secret-hardcoded-credential",
                            severity="High",
                            file=rel,
                            line=lineno,
                            message="Potential hardcoded credential/secret literal detected.",
                            evidence=redact_secret(literal, "generic"),
                        )
                    )

            if is_prose or is_comment_only(line):
                continue

            tls_match = TLS_DISABLE_RE.search(line)
            if tls_match:
                findings.append(
                    Finding(
                        scanner="builtin-static",
                        rule_id="config-tls-verify-disabled",
                        severity="High",
                        file=rel,
                        line=lineno,
                        message="TLS certificate verification is disabled.",
                        evidence=tls_match.group(1),
                    )
                )

            if YAML_LOAD_RE.search(line):
                window = "\n".join(lines[idx : min(len(lines), idx + 4)])
                if not SAFE_YAML_LOADER_RE.search(window):
                    findings.append(
                        Finding(
                            scanner="builtin-static",
                            rule_id="code-unsafe-yaml-load",
                            severity="High",
                            file=rel,
                            line=lineno,
                            message="yaml.load() called without SafeLoader/BaseLoader.",
                            evidence="yaml.load without SafeLoader",
                        )
                    )

            if SHELL_TRUE_RE.search(line):
                context_start = max(0, idx - 4)
                context_window = "\n".join(lines[context_start : idx + 1])
                if SUBPROCESS_CONTEXT_RE.search(context_window):
                    findings.append(
                        Finding(
                            scanner="builtin-static",
                            rule_id="code-subprocess-shell-true",
                            severity="Medium",
                            file=rel,
                            line=lineno,
                            message="Subprocess execution with shell=True enables command injection if input is untrusted.",
                            evidence="shell=True",
                        )
                    )

            if PICKLE_LOAD_RE.search(line):
                findings.append(
                    Finding(
                        scanner="builtin-static",
                        rule_id="code-unsafe-pickle",
                        severity="High",
                        file=rel,
                        line=lineno,
                        message="pickle.load/loads can execute arbitrary code on untrusted data.",
                        evidence=PICKLE_LOAD_RE.search(line).group(0).rstrip("("),
                    )
                )

    stats = {
        "files_scanned": len(files),
        "files_skipped_size": skipped_size,
        "files_skipped_binary": skipped_binary,
    }
    return findings, stats


def map_external_severity(raw: str | None, default: str = "Medium") -> str:
    if not raw:
        return default
    norm = raw.strip().lower()
    if norm in ("critical", "crit"):
        return "Critical"
    if norm in ("high", "error"):
        return "High"
    if norm in ("medium", "moderate", "warning", "warn"):
        return "Medium"
    if norm in ("low",):
        return "Low"
    if norm in ("info", "informational", "note"):
        return "Info"
    return default


def first_error_line(text: str) -> str:
    for line in text.splitlines():
        cleaned = line.strip()
        if cleaned:
            return cleaned[:160]
    return "non-zero exit status"


def run_gitleaks(target: Path, base: Path, timeout: int) -> tuple[dict[str, Any], list[Finding]]:
    exe = shutil.which("gitleaks")
    if not exe:
        return {"name": "gitleaks", "status": "unavailable", "reason": "not installed", "findings_count": 0}, []
    with tempfile.TemporaryDirectory() as tmpdir:
        report_path = Path(tmpdir) / "gitleaks.json"
        cmd = [
            exe,
            "detect",
            "--no-git",
            "--source",
            str(target),
            "--report-format",
            "json",
            "--report-path",
            str(report_path),
        ]
        try:
            proc = subprocess.run(cmd, shell=False, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return {"name": "gitleaks", "status": "timeout", "reason": f"exceeded {timeout}s", "findings_count": 0}, []
        except OSError as exc:
            return {"name": "gitleaks", "status": "error", "reason": str(exc), "findings_count": 0}, []

        if proc.returncode not in (0, 1):
            return {
                "name": "gitleaks",
                "status": "error",
                "reason": first_error_line(proc.stderr or proc.stdout),
                "findings_count": 0,
            }, []

        findings: list[Finding] = []
        if report_path.is_file():
            try:
                raw_data = json.loads(report_path.read_text(encoding="utf-8") or "[]")
            except (OSError, json.JSONDecodeError) as exc:
                return {"name": "gitleaks", "status": "error", "reason": f"invalid JSON report: {exc}", "findings_count": 0}, []
            if isinstance(raw_data, list):
                for item in raw_data:
                    if not isinstance(item, dict):
                        continue
                    file_val = str(item.get("File", ""))
                    fpath = Path(file_val)
                    rel = normalize_relpath(fpath, base) if fpath.is_absolute() else file_val.replace("\\", "/")
                    secret_val = str(item.get("Secret", ""))
                    findings.append(
                        Finding(
                            scanner="gitleaks",
                            rule_id=f"gitleaks-{item.get('RuleID', 'secret')}",
                            severity="High",
                            file=rel or ".",
                            line=int(item.get("StartLine", 0) or 0),
                            message=str(item.get("Description", "Secret detected by gitleaks.")),
                            evidence=redact_secret(secret_val, "prefix" if len(secret_val) > 8 else "generic"),
                        )
                    )
        return {"name": "gitleaks", "status": "ran", "reason": "", "findings_count": len(findings)}, findings


def run_osv_scanner(target: Path, base: Path, timeout: int) -> tuple[dict[str, Any], list[Finding]]:
    exe = shutil.which("osv-scanner")
    if not exe:
        return {"name": "osv-scanner", "status": "unavailable", "reason": "not installed", "findings_count": 0}, []
    cmd = [exe, "--format", "json", str(target)]
    try:
        proc = subprocess.run(cmd, shell=False, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"name": "osv-scanner", "status": "timeout", "reason": f"exceeded {timeout}s", "findings_count": 0}, []
    except OSError as exc:
        return {"name": "osv-scanner", "status": "error", "reason": str(exc), "findings_count": 0}, []

    if proc.returncode == 128:
        return {"name": "osv-scanner", "status": "skipped", "reason": "no supported lockfiles found", "findings_count": 0}, []
    if proc.returncode not in (0, 1):
        return {
            "name": "osv-scanner",
            "status": "error",
            "reason": first_error_line(proc.stderr or proc.stdout),
            "findings_count": 0,
        }, []

    findings: list[Finding] = []
    if proc.stdout.strip():
        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            return {"name": "osv-scanner", "status": "error", "reason": f"invalid JSON output: {exc}", "findings_count": 0}, []
        for result in payload.get("results", []) if isinstance(payload, dict) else []:
            source_path = str(result.get("source", {}).get("path", ""))
            rel = normalize_relpath(Path(source_path), base) if source_path else "."
            for pkg in result.get("packages", []):
                pkg_info = pkg.get("package", {})
                pkg_name = pkg_info.get("name", "unknown")
                pkg_ver = pkg_info.get("version", "")
                for vuln in pkg.get("vulnerabilities", []):
                    vuln_id = str(vuln.get("id", "OSV-UNKNOWN"))
                    summary = str(vuln.get("summary") or "Known dependency vulnerability.")
                    sev = map_external_severity(
                        (vuln.get("database_specific") or {}).get("severity"),
                        default="High",
                    )
                    findings.append(
                        Finding(
                            scanner="osv-scanner",
                            rule_id=vuln_id,
                            severity=sev,
                            file=rel,
                            line=0,
                            message=f"{pkg_name}@{pkg_ver}: {summary}",
                            evidence=vuln_id,
                        )
                    )
    return {"name": "osv-scanner", "status": "ran", "reason": "", "findings_count": len(findings)}, findings


def run_npm_audit(target: Path, timeout: int) -> tuple[dict[str, Any], list[Finding]]:
    if not target.is_dir() or not (target / "package-lock.json").is_file():
        return {"name": "npm-audit", "status": "skipped", "reason": "no package-lock.json in target root", "findings_count": 0}, []
    exe = shutil.which("npm")
    if not exe:
        return {"name": "npm-audit", "status": "unavailable", "reason": "not installed", "findings_count": 0}, []
    cmd = [exe, "audit", "--json"]
    try:
        proc = subprocess.run(cmd, cwd=str(target), shell=False, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"name": "npm-audit", "status": "timeout", "reason": f"exceeded {timeout}s", "findings_count": 0}, []
    except OSError as exc:
        return {"name": "npm-audit", "status": "error", "reason": str(exc), "findings_count": 0}, []

    try:
        payload = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return {
            "name": "npm-audit",
            "status": "error",
            "reason": first_error_line(proc.stderr or proc.stdout),
            "findings_count": 0,
        }, []

    if isinstance(payload, dict) and "error" in payload:
        err = payload["error"]
        msg = err.get("summary") if isinstance(err, dict) else str(err)
        return {"name": "npm-audit", "status": "error", "reason": str(msg or "npm audit error")[:160], "findings_count": 0}, []

    findings: list[Finding] = []
    vulns = payload.get("vulnerabilities") if isinstance(payload, dict) else None
    if isinstance(vulns, dict):
        for pkg_name, info in vulns.items():
            if not isinstance(info, dict):
                continue
            sev = map_external_severity(info.get("severity"), default="Medium")
            via = info.get("via", [])
            via_str = ", ".join(
                v.get("title", pkg_name) if isinstance(v, dict) else str(v)
                for v in (via if isinstance(via, list) else [])
            )
            findings.append(
                Finding(
                    scanner="npm-audit",
                    rule_id=f"npm-{pkg_name}",
                    severity=sev,
                    file="package-lock.json",
                    line=0,
                    message=f"Vulnerable npm package {pkg_name}: {via_str or 'advisory reported'}",
                    evidence=f"{pkg_name} ({info.get('range', 'unknown')})",
                )
            )
    return {"name": "npm-audit", "status": "ran", "reason": "", "findings_count": len(findings)}, findings


def run_pip_audit(target: Path, timeout: int) -> tuple[dict[str, Any], list[Finding]]:
    if not target.is_dir():
        return {"name": "pip-audit", "status": "skipped", "reason": "target is not a directory", "findings_count": 0}, []
    req_file = target / "requirements.txt"
    pyproject_file = target / "pyproject.toml"
    if not req_file.is_file() and not pyproject_file.is_file():
        return {
            "name": "pip-audit",
            "status": "skipped",
            "reason": "no requirements.txt or pyproject.toml in target root",
            "findings_count": 0,
        }, []
    exe = shutil.which("pip-audit")
    if not exe:
        return {"name": "pip-audit", "status": "unavailable", "reason": "not installed", "findings_count": 0}, []

    if req_file.is_file():
        cmd = [exe, "-r", str(req_file), "-f", "json"]
        manifest_name = "requirements.txt"
    else:
        cmd = [exe, str(target), "-f", "json"]
        manifest_name = "pyproject.toml"

    try:
        proc = subprocess.run(cmd, shell=False, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"name": "pip-audit", "status": "timeout", "reason": f"exceeded {timeout}s", "findings_count": 0}, []
    except OSError as exc:
        return {"name": "pip-audit", "status": "error", "reason": str(exc), "findings_count": 0}, []

    if proc.returncode not in (0, 1):
        return {
            "name": "pip-audit",
            "status": "error",
            "reason": first_error_line(proc.stderr or proc.stdout),
            "findings_count": 0,
        }, []

    findings: list[Finding] = []
    try:
        payload = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError as exc:
        return {"name": "pip-audit", "status": "error", "reason": f"invalid JSON output: {exc}", "findings_count": 0}, []

    deps = payload.get("dependencies", []) if isinstance(payload, dict) else []
    for dep in deps:
        if not isinstance(dep, dict):
            continue
        dep_name = dep.get("name", "unknown")
        dep_ver = dep.get("version", "")
        for vuln in dep.get("vulns", []):
            vuln_id = str(vuln.get("id", "PYSEC-UNKNOWN"))
            desc = str(vuln.get("description") or "Known Python dependency vulnerability.")[:180]
            findings.append(
                Finding(
                    scanner="pip-audit",
                    rule_id=vuln_id,
                    severity="High",
                    file=manifest_name,
                    line=0,
                    message=f"{dep_name}=={dep_ver}: {desc}",
                    evidence=vuln_id,
                )
            )
    return {"name": "pip-audit", "status": "ran", "reason": "", "findings_count": len(findings)}, findings


def run_semgrep(target: Path, base: Path, timeout: int) -> tuple[dict[str, Any], list[Finding]]:
    exe = shutil.which("semgrep")
    if not exe:
        return {"name": "semgrep", "status": "unavailable", "reason": "not installed", "findings_count": 0}, []
    cmd = [
        exe,
        "scan",
        "--config",
        "p/owasp-top-ten",
        "--json",
        "--metrics=off",
        "--quiet",
        str(target),
    ]
    try:
        proc = subprocess.run(cmd, shell=False, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"name": "semgrep", "status": "timeout", "reason": f"exceeded {timeout}s", "findings_count": 0}, []
    except OSError as exc:
        return {"name": "semgrep", "status": "error", "reason": str(exc), "findings_count": 0}, []

    try:
        payload = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return {
            "name": "semgrep",
            "status": "error",
            "reason": first_error_line(proc.stderr or proc.stdout),
            "findings_count": 0,
        }, []

    if proc.returncode not in (0, 1) and not payload.get("results"):
        return {
            "name": "semgrep",
            "status": "error",
            "reason": first_error_line(proc.stderr or proc.stdout),
            "findings_count": 0,
        }, []

    findings: list[Finding] = []
    for item in payload.get("results", []):
        if not isinstance(item, dict):
            continue
        raw_path = str(item.get("path", ""))
        fpath = Path(raw_path)
        rel = normalize_relpath(fpath, base) if fpath.is_absolute() else raw_path.replace("\\", "/")
        extra = item.get("extra", {}) or {}
        findings.append(
            Finding(
                scanner="semgrep",
                rule_id=str(item.get("check_id", "semgrep-rule")),
                severity=map_external_severity(extra.get("severity"), default="Medium"),
                file=rel or ".",
                line=int((item.get("start") or {}).get("line", 0) or 0),
                message=str(extra.get("message") or "Semgrep security finding."),
                evidence=str(item.get("check_id", "semgrep-rule")),
            )
        )
    return {"name": "semgrep", "status": "ran", "reason": "", "findings_count": len(findings)}, findings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_passive_checks.py",
        description=(
            "Run passive static security checks (secrets with redaction + risky config/code patterns) "
            "and auto-detected external scanners (gitleaks, osv-scanner, npm audit, pip-audit, semgrep)."
        ),
        epilog=(
            "Exit codes: 0 = 0 findings, 1 = 1+ findings detected, "
            "2 = invalid arguments or missing/unreadable target path."
        ),
    )
    parser.add_argument(
        "--target",
        default=".",
        help="Target directory or file to scan (default: current directory).",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format on stdout (default: text).",
    )
    parser.add_argument(
        "--max-findings",
        type=positive_int,
        default=50,
        metavar="N",
        help="Maximum findings returned before truncation (default: 50, must be >= 1).",
    )
    parser.add_argument(
        "--max-file-kb",
        type=positive_int,
        default=512,
        metavar="N",
        help="Skip files larger than N KB during built-in static scan (default: 512, must be >= 1).",
    )
    parser.add_argument(
        "--timeout",
        type=positive_int,
        default=60,
        metavar="N",
        help="Per-scanner timeout in seconds for external tools (default: 60, must be >= 1).",
    )
    parser.add_argument(
        "--skip-external",
        action="store_true",
        help="Run built-in static checks only and mark all external scanners as skipped.",
    )
    return parser


def format_text_report(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        f"Passive Security Check Report: {payload['target']}",
        (
            f"Files scanned: {summary['files_scanned']} | "
            f"Skipped (size): {summary['files_skipped_size']} | "
            f"Skipped (binary): {summary['files_skipped_binary']}"
        ),
        (
            f"Findings: {summary['total_findings']} total "
            f"(Critical={summary['severity_counts']['Critical']}, "
            f"High={summary['severity_counts']['High']}, "
            f"Medium={summary['severity_counts']['Medium']}, "
            f"Low={summary['severity_counts']['Low']}, "
            f"Info={summary['severity_counts']['Info']})"
        ),
        "",
        "Scanners:",
    ]
    for sc in payload["scanners"]:
        detail = f" ({sc['reason']})" if sc["reason"] else ""
        lines.append(f"  - {sc['name']}: {sc['status']}{detail} [findings={sc['findings_count']}]")

    lines.append("")
    if not payload["findings"]:
        lines.append("No findings detected by automated passive checks.")
    else:
        lines.append("Findings:")
        for item in payload["findings"]:
            loc = f"{item['file']}:{item['line']}" if item["line"] else item["file"]
            lines.append(
                f"  [{item['id']}] [{item['severity']}] {item['rule_id']} ({item['scanner']}) "
                f"at {loc} -- {item['message']} | evidence: {item['evidence']}"
            )

    if summary["truncated"]:
        lines.append("")
        lines.append(
            f"TRUNCATED: showing {summary['returned_findings']} of {summary['total_findings']} "
            f"findings ({summary['omitted_findings']} omitted). "
            f"Re-run with --max-findings {summary['total_findings']} or --format json to view all."
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    target = Path(args.target).resolve()
    if not target.exists():
        print(f"Error: target path does not exist: {target.as_posix()}", file=sys.stderr)
        return 2
    if not os.access(target, os.R_OK):
        print(f"Error: target path is not readable: {target.as_posix()}", file=sys.stderr)
        return 2

    base = target.parent if target.is_file() else target
    builtin_findings, stats = scan_builtin(target, args.max_file_kb)
    scanners: list[dict[str, Any]] = [
        {
            "name": "builtin-static",
            "status": "ran",
            "reason": "",
            "findings_count": len(builtin_findings),
        }
    ]
    all_findings: list[Finding] = list(builtin_findings)

    if args.skip_external:
        for name in EXTERNAL_SCANNERS:
            scanners.append(
                {
                    "name": name,
                    "status": "skipped",
                    "reason": "--skip-external specified",
                    "findings_count": 0,
                }
            )
    else:
        external_runners = (
            lambda: run_gitleaks(target, base, args.timeout),
            lambda: run_osv_scanner(target, base, args.timeout),
            lambda: run_npm_audit(target, args.timeout),
            lambda: run_pip_audit(target, args.timeout),
            lambda: run_semgrep(target, base, args.timeout),
        )
        for runner in external_runners:
            status_entry, ext_findings = runner()
            scanners.append(status_entry)
            all_findings.extend(ext_findings)

    all_findings.sort(
        key=lambda f: (
            SEVERITY_RANK.get(f.severity, 99),
            f.file,
            f.line,
            f.rule_id,
            f.scanner,
        )
    )

    severity_counts = {sev: 0 for sev in SEVERITY_RANK}
    for item in all_findings:
        severity_counts[item.severity] = severity_counts.get(item.severity, 0) + 1

    total_findings = len(all_findings)
    sliced = all_findings[: args.max_findings]
    omitted = max(0, total_findings - len(sliced))

    serialized_findings = [
        {
            "id": f"PASSIVE-{idx:03d}",
            "scanner": item.scanner,
            "rule_id": item.rule_id,
            "severity": item.severity,
            "file": item.file,
            "line": item.line,
            "message": item.message,
            "evidence": item.evidence,
        }
        for idx, item in enumerate(sliced, start=1)
    ]

    payload = {
        "target": target.as_posix(),
        "summary": {
            "files_scanned": stats["files_scanned"],
            "files_skipped_size": stats["files_skipped_size"],
            "files_skipped_binary": stats["files_skipped_binary"],
            "total_findings": total_findings,
            "returned_findings": len(serialized_findings),
            "truncated": omitted > 0,
            "omitted_findings": omitted,
            "severity_counts": severity_counts,
        },
        "scanners": scanners,
        "findings": serialized_findings,
    }

    if args.format == "json":
        print(json.dumps(payload, indent=2, ensure_ascii=True))
    else:
        print(format_text_report(payload))

    return 1 if total_findings > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
