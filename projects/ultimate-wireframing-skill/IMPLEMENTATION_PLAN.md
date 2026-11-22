# Implementation Plan: `ultimate-wireframing-skill`

- **Status:** Proposed (Blocked on Phase 0 Open Questions in [ADR.md](./ADR.md#7-open-questions-log))
- **Date:** 2026-11-21
- **Architecture Reference:** [ADR-001](./ADR.md)

---

## Guiding Engineering Principles

- **Contract first:** The `wire-spec` schema is the public API for both the studio and external AI agents. Validate strictly at the boundary and fail loudly on invalid input.
- **Single source of truth:** Visual tokens (Blueprint skin now, Sketchy later), component contracts, and file-envelope delimiters live in one canonical place—never hardcoded per component.
- **Deterministic output:** Identical `.wire.yaml` input always produces byte-identical layout and output artifacts (excluding explicit edit timestamps when modified).
- **Zero external runtime dependencies:** Python 3.9+ standard library (plus minimal YAML parser or strict subset parser) on the CLI side; plain dependency-free script (~20 KB budget) inside `.html` outputs so files stay tiny, fast, and 100% offline-capable.
- **Vertical slices:** Build end-to-end from `.wire.yaml` → `flow.html` → save-back → AI handoff verification before expanding component count.

---

## Phase 0: Spec Contract & Component Vocabulary Lock

Resolve [OQ-1 through OQ-5](./ADR.md#7-open-questions-log) before writing production code.

### Deliverables
1. **Schema specification (`spec-v1.md`):**
   - Lock YAML strictness vs. shorthand rules (**OQ-1**), including safe handling of colons, quotes, and boolean-like labels (`No`, `On`, `Off`).
   - Finalize top-level metadata (`app`, `context`, `shared`, `screens`) and per-screen fields (`id`, `updated_at`, `title`, `layout`, `items`).
   - Define Hybrid positioning representation: structured containers (`row`, `col`, `split`, `grid`) + optional freeform coordinates (`at: [x%, y%]`).
2. **v1 Component Role Catalog (~20 roles, OQ-2):**
   - Lock required/optional properties, visual hierarchy variants (`primary`, `secondary`, `ghost`, `danger`), navigation hooks (`go`, `open`), and behavioral hints (`states`, `note`, `data`).
3. **Top-of-File HTML Envelope Contract:**
   - Finalize the exact Lines 1–12 AI handoff comment header so cold AI agents stop at `</script>` and cleanly distinguish **Hi-Fi Mockup** generation from **Tech-Stack-Agnostic Code** generation.
4. **Golden Fixtures:**
   - Author 3 representative `.wire.yaml` fixtures: (1) simple auth/modal flow, (2) dense B2B dashboard + data table, (3) hybrid layout with pinned callouts/freeform elements.

---

## Phase 1: Core Compiler & Envelope Builder (`wire.py`)

Build the deterministic CLI foundation for reading, validating, compiling, and reconciling specs.

### Deliverables
1. **Parser & Boundary Validator:**
   - Parse `.wire.yaml` (and extract `<script id="wire-spec">` from `.html` files) with line-numbered validation errors.
   - Support reading and patching individual screens by `screen_id` so AI edits on multi-screen apps stay ~250–450 tokens.
2. **Build Pipeline (`wire.py build`):**
   - Compile 1 `.wire.yaml` into **1 combined multi-screen `flow.html`** by default.
   - Support `--only <screen-or-feature>` to emit **scoped `.html` files** (e.g., `checkout.html`) from the same `.wire.yaml`.
   - Pack the viewer runtime onto a single bottom line below `<!-- END OF AI SPEC -->`.
3. **Per-Screen Timestamp Reconciliation (`wire.py sync`):**
   - Compare `updated_at` per `screen_id` across `.wire.yaml` and existing `.html` files.
   - Automatically pull newer offline browser edits from any `.html` back into `.wire.yaml` before applying AI updates, flagging conflicts if the same `screen_id` diverged offline.
4. **Unit & Golden Tests:**
   - Round-trip tests verifying `.wire.yaml` → `flow.html` + `checkout.html` → per-screen merge back into `.wire.yaml` with zero data loss.

---

## Phase 2: Single-File `.html` Viewer & Clean Blueprint Skin

Build the dependency-free interactive wireframe player and Clean Blueprint theme inside the ~20 KB runtime budget.

### Deliverables
1. **Theme & Skin Token Layer:**
   - Define abstract visual tokens (spacing density, monochrome Blueprint strokes/fills, typography scale, component chrome) cleanly separated from component structure so a **Sketchy** skin can be added in Phase 5 without touching components.
2. **Core Layout & Component Renderer:**
   - Render structured containers (`row`, `col`, `split`, `grid`, `shared` topbar/sidebar) plus freeform pinned elements (`at: [x%, y%]`).
   - Implement the ~20 stack-agnostic v1 UI components in **Clean Blueprint** style, including empty/warning/active states.
3. **Multi-Screen Flow Navigation:**
   - Screen switcher tabs, clickable `go:` / `open:` hotspots (screen transitions, modals, drawers), and state preview toggles.
4. **1-Click `.svg` & `.png` Export:**
   - Export clean, layered `<svg>` (for GitHub/Jira/Confluence docs and direct paste into Figma) and `.png` snapshots directly from the studio toolbar, plus CLI snapshot export in `wire.py build`.

---

## Phase 3: Hybrid Visual Studio & Two-Mode Save Sync

Turn the `.html` viewer into a fast drag-and-drop wireframe editor with seamless round-trip persistence.

### Deliverables
1. **Direct Manipulation UX:**
   - Double-click inline text/label editing on any component.
   - Component insertion palette, delete/duplicate shortcuts, and undo/redo history stack.
2. **Hybrid Drag-and-Drop Engine:**
   - **Structured mode (default):** Drag items to reorder within containers, move across rows/columns, and drag split dividers to adjust column proportions.
   - **Freeform override:** Pin/unpin toggle (or modifier drag) placing an element at relative `at: [x%, y%]` coordinates without disturbing sibling auto-layout.
3. **Dual Save-Back Modes:**
   - **Mode A (`wire.py edit` background helper):** Lightweight localhost watcher (auto-started by AI) providing instant, dialog-free two-way live sync between the open browser tab, `.wire.yaml`, all generated `.html` views, and `.svg` snapshots.
   - **Mode B (Standalone `file://` double-click):** Rewrites `<script id="wire-spec">` at the top of the `.html` file and saves in place via Chrome/Edge file-overwrite permission (1-time confirmation, then `Ctrl+S`), with download + Copy Spec fallback for Safari/Firefox.

---

## Phase 4: AI Skill Packaging & Blind Handoff Verification

Package the workflow as a portable agent skill and verify cold-AI handoff quality across both code and hi-fi design tasks.

### Deliverables
1. **Agent Skill (`SKILL.md`):**
   - Concise instructions teaching authoring agents how to write `.wire.yaml`, patch screens by `screen_id`, auto-launch `wire.py edit`, and reserve vision screenshots strictly for optional visual QA.
2. **End-to-End & Cold-Handoff Benchmarks:**
   - **Token benchmark:** Confirm authoring and single-screen edit loops stay within ~250–450 tokens per enterprise screen.
   - **Blind Code Handoff Test:** Point cold AI sessions (with **no** wireframing skill loaded) at `flow.html` inside sample React, Angular/.NET, and mobile projects; verify they stop at `</script>`, ignore viewer code, and map components natively.
   - **Blind Hi-Fi Mockup Test:** Point cold AI sessions at `flow.html` to generate hi-fi visual mockups; verify layout proportions, user flows, and `context` styling hints transfer accurately.

---

## Phase 5: Future Extensions (Post-v1)

1. **Sketchy / Hand-Drawn Skin:** Plug a Balsamiq-style sketchy stroke/font renderer into the Phase 2 skin contract (`skin: blueprint | sketchy`).
2. **Zero-Install Web Playground:** Deploy a blank studio to GitHub Pages for instant browser sketching without local files.
