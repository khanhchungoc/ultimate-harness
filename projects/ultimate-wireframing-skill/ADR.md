# ADR-001: Zero-Install AI Wireframing Architecture

- **Status:** Draft (Core Architecture Agreed; Spec Schema Open)
- **Date:** 2026-11-21
- **Project:** `ultimate-wireframing-skill`
- **Related Plan:** [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md)

---

## 1. Context & Problem Statement

AI-assisted wireframing suffers from a structural trilemma: **token-efficient text** (for LLMs and Git), **visual drag-and-drop editing** (for fast human iteration and stakeholder alignment), and **semantic structure** (for clean handoff to hi-fi mockups or production code) pull in opposite directions.

Existing open-source repositories, MCP servers, and agent skills break down across **six recurring pain points**:

1. **Expensive, slow MCP loops:** Remote or heavy local MCP servers add OAuth friction, setup overhead, and slow multi-turn tool calls.
2. **Not manually editable:** Code-generated wireframes force users to re-prompt an AI or edit layout code just to move a button or rename a label.
3. **Bulky HTML/JSON generation:** Asking an LLM to emit raw HTML, CSS, or canvas JSON burns thousands of tokens per screen and produces unreadable Git diffs.
4. **Hard to share:** Local multi-file prototypes or proprietary canvas files do not preview natively in Jira, Confluence, Slack, or GitHub PRs.
5. **Wireframe → Code / Hi-Fi dead end:** Once a wireframe is edited visually on a whiteboard (Whimsical, Excalidraw, Draw.io), it drifts out of sync with written specs and must be rebuilt from scratch for hi-fi design or engineering.
6. **Fragile ASCII wireframes:** Plain-text/ASCII wireframes are cheap for LLMs to write, but break easily during edits and fail for stakeholder alignment.

### Core Design Principles

1. **Zero-install, universal viewing:** Output files must open natively in standard web browsers and documentation tools on any OS—no desktop apps, IDE plugins, or SaaS accounts required.
2. **Coordinate-free by default:** Wireframes express hierarchy, grouping, and relative proportions rather than pixel coordinates. LLMs should not compute `(x, y, width, height)` math; deterministic layout rules handle positioning automatically unless a human explicitly pins an element out of flow.

---

## 2. Landscape Survey: Existing Tools & Skills

Existing solutions fall into three categories, each solving half the problem while failing the rest:

| Tool / Repo | Architecture | Avoids Slow MCP? | Manually Editable? | Avoids Bulky Markup? | Easy to Share? | Clean Code / Hi-Fi Handoff? | Better Than ASCII? |
|---|---|---|---|---|---|---|---|
| `agilek/wireframer-skill` | HTML/React Code-Gen | Yes (Pure skill) | No (Code edits) | No (Bulky SPA) | Partial (Needs host/zip) | Partial (Web-only code) | Yes (Balsamiq look) |
| `mockflow/wireframepro-mcp` | SaaS Canvas MCP | No (MCP + SaaS) | Yes (Drag & drop) | No (Inline HTML) | Yes (Share URL) | Partial (Rough export) | Yes (Balsamiq look) |
| `WhimsicalCode/skills` | SaaS Canvas MCP | No (OAuth MCP) | Yes (Drag & drop) | Yes (Board API) | Yes (Board URL) | No (Dead end) | Yes (Clean lo-fi) |
| `yctimlin/mcp_excalidraw` | Canvas MCP | No (Heavy MCP) | Yes (Drag & drop) | Yes (JSON canvas) | Yes (`.excalidraw`) | No (Dead end) | Yes (Hand-drawn) |
| `enlinks-llc/katsuragi` | Compact Text DSL | Yes (Pure CLI) | Partial (Text only) | Yes (~50% smaller) | Partial (Static PNG) | Partial (Basic grid) | Yes (Rendered PNG) |
| `jgraph/drawio-mcp` | Canvas MCP | No (MCP) | Yes (Drag & drop) | Partial (Verbose XML) | Yes (`.drawio` / PNG) | No (Dead end) | Yes (Clean diagrams) |
| `jpoindexter/wireframe-skills` | Process Markdown | Yes (Pure docs) | N/A | N/A | N/A | No (No renderer) | No (Text / ASCII) |
| `PlantUML Salt` | Docs-as-Code DSL | Yes (Pure text) | No (Text only) | Yes (Tiny syntax) | Yes (Docs / PNG) | No (Dead end) | Partial (Dated look) |
| `Wireweave (@wireweave/core)` | AI Wireframe DSL | Optional (CLI/MCP) | No (No visual drag) | Yes (Compact DSL) | Partial (HTML/IDE) | Partial (Web export) | Yes (Clean lo-fi) |
| `Frame0 (frame0-mcp-server)` | Desktop App + MCP | No (App + MCP) | Yes (Drag & drop) | Yes (Tool calls) | Partial (Exports) | No (App lock-in) | Yes (Hand-drawn) |
| `Pencil.dev (.pen)` | IDE Canvas + MCP | No (IDE + MCP) | Yes (Drag & drop) | Yes (Repo `.pen`) | Partial (Needs IDE) | Yes (Code-oriented) | Yes (Hi-fi/lo-fi) |

*(Note: Infinite sketchboards such as `tldraw` excel at converting human sketches into code, but do not solve AI-generated structured multi-screen wireframes with round-trip sync.)*

---

## 3. Target Output Options Evaluated

All candidates share a **2-layer decoupled design**: the AI authors a compact semantic YAML tree, and a local Python compiler (`wire.py`) renders visual artifacts.

### Target Format Comparison

| Dimension | Option A: YAML ↔ `.excalidraw` | Option B: Self-Editing Smart `.svg` | Option C: Single-File `.html` Studio (Chosen) |
|---|---|---|---|
| **Zero Extra App Installs** | Needs VS Code plugin or web import | Opens natively in any browser/OS | Opens natively in any browser/OS |
| **Passive Previews (GitHub, Jira, Confluence, Slack)** | Requires exporting `.excalidraw.png` | Native image preview (scripts stripped) | Needs companion `.svg` / `.png` export |
| **Manual Editor UX (Menus, Palette, Inline Text)** | Mature freeform whiteboard | Fragile toolbar/input support inside SVG | Full palette, menus, undo/redo, inline text edit |
| **Multi-Screen Clickable Flows** | Single infinite canvas only | Single screen per file | Native screen tabs + clickable hotspots |
| **Claude Artifacts & Static Web Hosting** | Not natively playable | Sandboxes block embedded SVG scripts | Runs natively with full interactivity |
| **AI Read-Back / Round-Trip Sync** | Noisy reverse-sync via `customData` | Reads `<metadata id="wire-spec">` | Reads top `<script id="wire-spec">` block |

### AI Read-Back Method Comparison

| Read-Back Method | Typical Token Cost (Enterprise Screen) | Spatial & Semantic Accuracy | Role in Workflow |
|---|---|---|---|
| **Raw `.html` / `.svg` Markup** | ~2,500 – 4,000+ tokens | Poor (buried in styling/viewer boilerplate) | **Never use** (85%–90% token waste; contaminates target tech stack) |
| **Screenshot (Vision / VLM)** | ~500 – 800+ tokens | Weak on exact hierarchy; blind to component IDs and flow links | **Optional visual QA only (~5% of calls)** to check text clipping or visual balance |
| **Embedded YAML Block (`wire-spec`)** | ~100 – 150 tokens (simple card)<br>~250 – 450 tokens (enterprise screen) | 100% exact (preserves IDs, roles, flow targets, notes, and layout overrides) | **Default AI loop (~95% of calls)** for edits, Git diffs, hi-fi mockups, and code handoff |

---

## 4. Hidden Architectural Traps Surfaced & Mitigations

During session review, five practical failure modes were identified and resolved:

### Trap 1: Browser Save-Back Security & Source-of-Truth Drift
- **Problem:** Web browsers block local files opened via double-click (`file://`) from silently overwriting themselves or rebuilding multiple sibling files on disk. Pressing `Ctrl+S` saves the unedited original file, and browser downloads create duplicate `flow (1).html` copies.
- **Mitigation:** Support two seamless save modes backed by per-screen timestamps:
  - **Mode A (Live AI Session — `wire.py edit`):** Automatically started in the background by the AI (Python standard library only, zero user terminal steps). Opens the browser on `localhost` with instant two-way auto-save across `.wire.yaml`, `.html`, and `.svg` files.
  - **Mode B (Standalone / Teammate Double-Click):** When opened without `wire.py` running, Chrome/Edge uses native file-overwrite permission (prompts once on first Save, then `Ctrl+S` overwrites in place); Safari/Firefox falls back to file download + Copy Spec.
  - **Safe Auto-Reconciliation:** Stamp each screen with `id` and `updated_at`. Before applying new AI changes, `wire.py` checks whether any `.html` file holds newer offline human edits and imports them into `.wire.yaml` per `screen_id` automatically.

### Trap 2: Coordinate-Free Auto-Layout vs. Manual Drag-and-Drop
- **Problem:** Writing raw pixel coordinates back into YAML whenever a human drags an item breaks responsive reflow and causes overlaps on the next AI edit.
- **Mitigation:** Use a **Hybrid Layout Model**. Default drag-and-drop to **structured slot operations** (reordering items, moving across rows/columns/sidebars, and dragging column dividers to adjust width ratios). Allow optional **freeform placement (`at: [x%, y%]`)** per individual element only when explicitly pinned/dragged out of container flow.

### Trap 3: Dual-Renderer Drift (`.html` View vs. `.svg` Snapshots)
- **Problem:** Maintaining two independent layout/text-wrapping engines in Python and browser script causes visual mismatches between the interactive `.html` studio and exported `.svg` docs.
- **Mitigation:** Drive layout from deterministic rules and serialize clean, layered `<svg>` snapshots directly from the exact rendered geometry (enabling identical `.svg`/`.png` doc exports and direct copy-paste into Figma as editable vector layers).

### Trap 4: Multi-Screen Token Scaling & YAML Edge Cases
- **Problem:** A 6-screen enterprise flow reaches ~1,500–2,500 tokens, and standard YAML trips LLMs on unquoted colons (`Warning: Delete item?`), boolean coercion (`No`, `On`, `Off`), and deep nesting.
- **Mitigation:** Support reading/updating individual screens by `screen_id`, keep shorthand syntax flat where possible, and validate inputs strictly at the compiler boundary with clear error messages.

### Trap 5: Tech-Stack Contamination During Handoff
- **Problem:** Pointing a coding AI at an ordinary HTML prototype causes it to copy web-specific viewer markup instead of using the target repository's native stack (React, Angular, Vue, .NET Blazor, SwiftUI, Flutter, etc.).
- **Mitigation:** Place a plain-English **AI Handoff Instruction Header** at Lines 1–12 of every `.html` file instructing any AI to stop reading at `</script>`, ignore the compressed 1-line viewer runtime at the bottom, and map neutral component roles (`table`, `card`, `field`, `button.primary`) to the target stack or hi-fi design context.

---

## 5. Locked-In Decisions Summary

1. **Master Source & Multi-HTML Support:**
   - **1 `.wire.yaml`** serves as the master source for a project/flow and supports generating **both** a combined multi-screen `flow.html` (default) and scoped per-feature or per-screen `.html` files (e.g., `checkout.html`) on demand, alongside static `screen-*.svg` snapshots.
   - Save-back merges changes by **`screen_id` + `updated_at`**, so editing a single-screen `.html` never overwrites other screens in `.wire.yaml`.
2. **Zero-Terminal User Experience:**
   - Users never manually start servers during AI workflows; the AI launches `wire.py edit` automatically. Offline users simply double-click `.html`.
3. **Hybrid Canvas Editing:**
   - Structured auto-layout containers (`row`, `col`, `split`, `grid`) by default + optional per-element freeform placement (`at: [x%, y%]`).
4. **Clean Blueprint v1, Scalable to Sketchy:**
   - Launch with a crisp monochrome **Clean Blueprint** visual skin mapped to modern UI components. Decouple all styling through a skin/token contract so a hand-drawn **Sketchy** skin can be added later without changing `.wire.yaml` files or layout logic.
5. **Zero-UI, Direct-File AI Handoff:**
   - **Rejected** manual "Handoff / Inspect Mode" panels and copy-prompt buttons.
   - **Adopted** direct file handoff: the user points any cold AI agent straight at `flow.html` to build **either a Hi-Fi Mockup or Production Code**. The top of `flow.html` contains self-bootstrapping AI instructions + `<script id="wire-spec" type="text/yaml">`, and browser saves rewrite that top block so `flow.html` is always up to date. Runtime script stays lean (~20 KB on a single bottom line, zero frameworks).

---

## 6. Candidate Top-of-File Handoff Envelope (Reference Draft)

*Note: Structure below is a reference draft from brainstorming; exact YAML strictness and field granularity remain open under **OQ-1**.*

```yaml
# <!-- AI HANDOFF: Read ONLY this wire-spec block. Ignore viewer runtime after </script>.
# For CODE: implement using the target repo's native UI stack & router; never copy viewer HTML.
# For HI-FI MOCKUP: preserve layout ratios, hierarchy & flows; elevate visuals to match `context`. -->
<script id="wire-spec" type="text/yaml">
app: B2B Order Portal
context: { viewport: 1280x800, density: compact, style-hint: clean enterprise SaaS }

shared:
  sidebar: [Orders (active -> orders), Customers -> customers, Settings]

screens:
  - id: orders
    updated_at: "2026-11-21T23:30:00Z"
    title: Orders
    layout: col
    items:
      - row (spread):
          - heading: Orders
          - button.primary: "+ New Order" -> new-order-modal
      - grid (cols: 3):
          - stat: { label: Pending, value: "24" }
          - stat: { label: Shipped Today, value: "118" }
          - stat: { label: Issues, value: "2", tone: warning }
      - table:
          columns: [Order ID, Customer, Status, Total]
          on_row_click: -> order-detail
          states: { empty: "No orders yet — create your first order" }
</script>
<!-- END OF AI SPEC — compressed 1-line viewer studio sits below -->
```

---

## 7. Open Questions Log

| ID | Topic | Question to Resolve | Options / Considerations |
|---|---|---|---|
| **OQ-1** | **YAML Spec Strictness & Granularity** *(Logged from session)* | How strict vs. flexible should the `wire-spec` YAML syntax and detail level be? | **Strict structured schema** (predictable parsing, slightly more verbose) vs. **compact shorthand strings** (`button.primary: "+ New Order" -> modal`, fewer tokens, needs custom shorthand parser) vs. **minimal loose tree** (fewer fields like `context`/`states`, faster to write, but cold AIs infer more during hi-fi/code generation). |
| **OQ-2** | **Core v1 Component Vocabulary** | Which exact ~15–20 stack-agnostic UI roles belong in v1? | Candidate set: `page`, `topbar`, `sidebar`, `tabs`, `split`, `row`, `col`, `grid`, `card`, `stat`, `table`, `list`, `heading`, `text`, `field`, `select`, `checkbox`, `switch`, `button`, `badge`, `alert`, `modal`, `drawer`, `placeholder/chart`. |
| **OQ-3** | **Offline `.svg` Build Pipeline** | How should `wire.py build` generate static `.svg` files when no browser is open? | Pure-Python deterministic box layout emitting SVG (requires matching browser text-wrapping closely) vs. shared layout logic / headless snapshot when exporting docs via CLI. |
| **OQ-4** | **Offline Concurrent Screen Conflict** | What happens if two teammates edit the *same* `screen_id` offline in `flow.html` and `checkout.html`? | Keep both versions side-by-side (`orders` and `orders-conflict-copy`) and warn loudly vs. prompt user to pick winner in CLI/studio. |
| **OQ-5** | **Repository & Skill Packaging** | Where should the production codebase live? | Dedicated standalone repo (like `ultimate-diagraming-skill` with automated golden/e2e tests and optional GitHub Pages blank studio) linked into `ultimate-harness`, vs. self-contained inside `.agents/skills/`. |
