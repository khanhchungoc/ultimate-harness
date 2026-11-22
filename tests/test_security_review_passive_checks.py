"""Unit tests for .agents/skills/security-review/scripts/run_passive_checks.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = (
    REPO_ROOT
    / ".agents"
    / "skills"
    / "security-review"
    / "scripts"
    / "run_passive_checks.py"
)


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), *args],
        capture_output=True,
        text=True,
        check=False,
    )


class TestSecurityReviewPassiveChecks(unittest.TestCase):
    def test_clean_directory_returns_zero_in_text_and_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "app.py").write_text(
                "import os\n"
                "import yaml\n"
                "API_KEY = os.environ.get('API_KEY')\n"
                "data = yaml.safe_load('a: 1')\n",
                encoding="utf-8",
            )

            text_proc = run_cli("--target", str(root), "--skip-external", "--format", "text")
            self.assertEqual(text_proc.returncode, 0, msg=text_proc.stderr)
            self.assertIn("No findings detected", text_proc.stdout)

            json_proc = run_cli("--target", str(root), "--skip-external", "--format", "json")
            self.assertEqual(json_proc.returncode, 0, msg=json_proc.stderr)
            payload = json.loads(json_proc.stdout)
            self.assertEqual(payload["summary"]["total_findings"], 0)
            self.assertEqual(payload["summary"]["files_scanned"], 1)
            self.assertEqual(payload["findings"], [])

    def test_detects_secrets_and_redacts_raw_values(self) -> None:
        aws_key = "AKIA" + "0123456789ABCDEF"
        gh_token = "ghp_" + "a1b2c3d4e5f6g7h8i9j0k1l2m3n4"
        stripe_key = "sk_live_" + "99887766554433221100aabb"
        slack_token = "xoxb-" + "1234567890-abcdef123456"
        generic_pw = "Tr0ub4dor&3_LiveSecret99!"
        priv_header = "-----BEGIN " + "RSA PRIVATE KEY-----"

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "secrets.py").write_text(
                f'AWS_ACCESS_KEY_ID = "{aws_key}"\n'
                f'GITHUB_TOKEN = "{gh_token}"\n'
                f'STRIPE_KEY = "{stripe_key}"\n'
                f'SLACK_BOT_TOKEN = "{slack_token}"\n'
                f'db_password = "{generic_pw}"\n'
                f'KEY_PEM = "{priv_header}"\n',
                encoding="utf-8",
            )

            for fmt in ("text", "json"):
                proc = run_cli("--target", str(root), "--skip-external", "--format", fmt)
                self.assertEqual(proc.returncode, 1, msg=proc.stderr)
                # Raw secrets must NEVER appear in stdout or stderr
                combined = proc.stdout + proc.stderr
                self.assertNotIn(aws_key, combined)
                self.assertNotIn(gh_token, combined)
                self.assertNotIn(stripe_key, combined)
                self.assertNotIn(slack_token, combined)
                self.assertNotIn(generic_pw, combined)
                self.assertNotIn(priv_header, combined)

            payload = json.loads(
                run_cli("--target", str(root), "--skip-external", "--format", "json").stdout
            )
            rules = {item["rule_id"] for item in payload["findings"]}
            self.assertIn("secret-aws-access-key", rules)
            self.assertIn("secret-github-token", rules)
            self.assertIn("secret-stripe-live-key", rules)
            self.assertIn("secret-slack-token", rules)
            self.assertIn("secret-hardcoded-credential", rules)
            self.assertIn("secret-private-key", rules)

    def test_detects_risky_patterns_without_safe_false_positives(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "risky.py").write_text(
                "import pickle\n"
                "import subprocess\n"
                "import yaml\n"
                "import requests\n"
                "requests.get('https://example.internal', verify=False)\n"
                "yaml.load(raw_text)\n"
                "subprocess.run('ls -la', shell=True)\n"
                "pickle.loads(raw_bytes)\n",
                encoding="utf-8",
            )
            (root / "tls.js").write_text(
                "const agent = new https.Agent({ rejectUnauthorized: false });\n",
                encoding="utf-8",
            )
            (root / "safe.py").write_text(
                "import os\n"
                "import yaml\n"
                "password = 'changeme'\n"
                "api_key = 'your_api_key_here'\n"
                "tpl = f'db_password = \"{user_password}\"'\n"
                "token = os.environ['API_KEY']\n"
                "a = yaml.safe_load(raw_text)\n"
                "b = yaml.load(raw_text, Loader=yaml.SafeLoader)\n",
                encoding="utf-8",
            )

            proc = run_cli("--target", str(root), "--skip-external", "--format", "json")
            self.assertEqual(proc.returncode, 1, msg=proc.stderr)
            payload = json.loads(proc.stdout)
            rules = {item["rule_id"] for item in payload["findings"]}
            files = {item["file"] for item in payload["findings"]}

            self.assertIn("config-tls-verify-disabled", rules)
            self.assertIn("code-unsafe-yaml-load", rules)
            self.assertIn("code-subprocess-shell-true", rules)
            self.assertIn("code-unsafe-pickle", rules)
            self.assertIn("risky.py", files)
            self.assertIn("tls.js", files)
            self.assertNotIn("safe.py", files)

    def test_skips_ignored_dirs_binary_and_oversized_files(self) -> None:
        aws_key = "AKIA" + "9876543210FEDCBA"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # Ignored directories containing secrets should never be scanned
            (root / "node_modules" / "pkg").mkdir(parents=True)
            (root / "node_modules" / "pkg" / "index.js").write_text(
                f'const k = "{aws_key}";\n', encoding="utf-8"
            )
            (root / ".git").mkdir()
            (root / ".git" / "config").write_text(f"token = {aws_key}\n", encoding="utf-8")

            # Binary file (NUL byte)
            (root / "blob.bin").write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00" + aws_key.encode())

            # Oversized file (> 1 KB)
            (root / "large.txt").write_text(("a" * 2048) + f"\n{aws_key}\n", encoding="utf-8")

            # Clean small file
            (root / "clean.py").write_text("x = 1\n", encoding="utf-8")

            proc = run_cli(
                "--target",
                str(root),
                "--skip-external",
                "--max-file-kb",
                "1",
                "--format",
                "json",
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            payload = json.loads(proc.stdout)
            summary = payload["summary"]
            self.assertEqual(summary["files_scanned"], 1)
            self.assertEqual(summary["files_skipped_binary"], 1)
            self.assertEqual(summary["files_skipped_size"], 1)
            self.assertEqual(summary["total_findings"], 0)

    def test_enforces_max_findings_truncation_transparency(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lines = [f"requests.get('https://x/{i}', verify=False)" for i in range(5)]
            (root / "many.py").write_text("\n".join(lines) + "\n", encoding="utf-8")

            json_proc = run_cli(
                "--target",
                str(root),
                "--skip-external",
                "--max-findings",
                "2",
                "--format",
                "json",
            )
            self.assertEqual(json_proc.returncode, 1)
            payload = json.loads(json_proc.stdout)
            summary = payload["summary"]
            self.assertTrue(summary["truncated"])
            self.assertEqual(summary["total_findings"], 5)
            self.assertEqual(summary["returned_findings"], 2)
            self.assertEqual(summary["omitted_findings"], 3)
            self.assertEqual(len(payload["findings"]), 2)

            text_proc = run_cli(
                "--target",
                str(root),
                "--skip-external",
                "--max-findings",
                "2",
                "--format",
                "text",
            )
            self.assertEqual(text_proc.returncode, 1)
            self.assertIn("TRUNCATED: showing 2 of 5 findings (3 omitted)", text_proc.stdout)

    def test_invalid_arguments_and_missing_target_return_exit_code_2(self) -> None:
        missing = run_cli("--target", "/nonexistent/path/for/security-review-test")
        self.assertEqual(missing.returncode, 2)
        self.assertIn("does not exist", missing.stderr)

        bad_max = run_cli("--target", str(REPO_ROOT), "--max-findings", "0")
        self.assertEqual(bad_max.returncode, 2)

        bad_kb = run_cli("--target", str(REPO_ROOT), "--max-file-kb", "0")
        self.assertEqual(bad_kb.returncode, 2)

        bad_timeout = run_cli("--target", str(REPO_ROOT), "--timeout", "0")
        self.assertEqual(bad_timeout.returncode, 2)

    def test_skip_external_marks_all_external_scanners_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "package-lock.json").write_text("{}", encoding="utf-8")
            (root / "requirements.txt").write_text("requests==2.31.0\n", encoding="utf-8")

            proc = run_cli("--target", str(root), "--skip-external", "--format", "json")
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)
            payload = json.loads(proc.stdout)
            scanners = {entry["name"]: entry for entry in payload["scanners"]}
            self.assertEqual(scanners["builtin-static"]["status"], "ran")
            for name in ("gitleaks", "osv-scanner", "npm-audit", "pip-audit", "semgrep"):
                self.assertIn(name, scanners)
                self.assertEqual(scanners[name]["status"], "skipped")
                self.assertIn("--skip-external", scanners[name]["reason"])


if __name__ == "__main__":
    unittest.main()
