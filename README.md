# ultimate-harness

Shared agent harness: global rules, reusable skills, and MCP templates installed once per machine so project repositories stay clean.

## Structure

- `AGENTS.md` — global instructions (CodeGraph usage, always-on modes, exceptions, general coding principles)
- `skills/` — shared skills (`caveman`, `motion`, `ponytail`, `ultracave`)
- `mcp/` — reference MCP / hook configs (`mcp.json`, `codex.toml`, `claude-settings.json`)
- `install.py` — Python 3.9+ stdlib installer for Antigravity, Claude Code, Codex, Gemini CLI, and Kiro

## Usage

Preview changes:

```sh
python install.py --dry-run
```

Link (or copy as fallback) globally for all supported runtimes:

```sh
python install.py
```

Options:

- `--runtime all|antigravity|claude|codex|gemini|kiro` (default: `all`)
- `--mode link|copy` (default: `link`)
- `--dry-run` — print planned actions without modifying files
- `--force` — overwrite existing non-link files or directories
