## Motion

- **Motion skill, every task.** For any task that touches animation, transitions, or UI motion (including actions that add or change interactive behaviour), invoke the global `motion` skill first and follow it. Repo principle: **morph, not fade**. An element that changes state, position or shape animates from its old geometry to its new one (see `morphRect`, `morphRing`, `ghostMorph` in `assets/shell/shell.js`); never cross-fade or fade in/out as a substitute.

## Coding principles

- **Maintainable and scalable.** Code must stay easy to maintain and scale to every diagram type and size, from a handful of nodes to thousands. A change that works for one type or small diagram but breaks or slows down another is not done.
- **Reuse and DRY.** Search `assets/components`, `assets/shell`, and `scripts/` first, and extend an existing helper or component before adding new code. Reuse `ui.actionBar`, `swatchPicker` (hover color picker), `ui.noteCard` + `.note-badge` (`note-lines` icon), `ui.toast`, and `dock.css` container styling (`--radius-xl`, `20px` outer inset); hide `#btn-delete-selection` per-type when the action bar owns Delete. Share across diagram types through `assets/components` and `assets/shell` (extract on the third copy, never if sharing would couple two types).
- **Shared UI elements.** Collapse chevrons (`ui.chevron`), connection ports (`ui.port`, `port.css`), edge labels (`edge.css`), the hover / selected / dimmed look (`item-states.css`: `data-item`, `.item-shape`) and notes (`createNotes` in `assets/shell/notes.js`) are defined once; the inventory is `dev/docs/ui-elements.md`. A type only positions them, uses the state names `.selected`, `.is-editing`, `.is-collapsed`, `.is-dim`, `.is-dragging`, and never restyles or copies them (`dev/tests/unit/check_components.py` fails on a copy; a justified exception carries `components-ok: <reason>`). A new shared element goes into the inventory, the gallery (`dev/playground/components.html`) and the checker in the same change.
- **Single source of truth (SSOT).** Tokens live in `assets/tokens` and `scripts/tokens.py`, layout in `scripts/layout_engine.py`, the file format in `scripts/disk_format.py`, and the type list in `SUPPORTED_TYPES`. Never copy these into a type, component, or playground, and never hardcode colors, sizes, or fonts.
- **Vertical slices.** One diagram type is one complete slice: its folder, `blank.json`, `dev/playground/<type>.json`, `e2e_playground.mjs` `menuIds`, example, checker or e2e test, and docs (including `SKILL.md` frontmatter `description` and type table) in the same change, built on the shared UI elements above.
- **SOLID, kept light.** The shell and layout engine are open for extension and closed for modification: a new type plugs in through a contract, and core code is not edited per type. Keep component APIs small. Prefer small modules and plain functions; use classes only for real state or polymorphism, not as a rule.
- **Contract first.** The disk format is the public API. Changing it needs a migration and a golden test (`dev/tests/unit/check_golden.py`).
- **Deterministic.** The same input must always give the same layout and output: no randomness, no time-based values.
- **Validate at the edge.** Check input once at the boundary and fail loudly, then trust it inside.
- **Verify commands.** Iteration & merges to `stg`: `npm run test:fast:changed` (plus a single targeted E2E via `node dev/tests/run_e2e.mjs --only <id> --exact --section <sec>` only when verifying a specific UI behavior; split multi-diagram UI changes into 1-diagram slices/PRs). PR to `main` (production): changed-items E2E across `origin/main..origin/stg` (`npm run test:e2e:changed`, or `npm run test:e2e`, plus `--perf` before releases), light/dark contrast, and—when `assets/` or page-assembly scripts changed—`python3 dev/tools/build_examples.py && python3 dev/tools/build_examples.py --check`.
- **Visual check before handoff.** For a new diagram type or major UI/CSS change, capture and visually inspect light + dark screenshots (and key view/zoom modes) via `node dev/tools/capture_review.mjs --page <html-file> --themes light,dark` before presenting to the user; DOM E2E assertions alone do not catch visual overlap, clipping, or hierarchy defects. Use versioned filenames (`_v2`, `_v3`) when refreshing screenshot preview artifacts to avoid viewer caching.
- **No new dependencies** without a stated reason; the skill must stay portable.

## Implementation plans

Implementation plans live in `dev/plans/`. Once all phases of a plan are complete, mark the plan as completed and move it into `dev/plans/archive/`.

## Playground (GitHub Pages)

Both playgrounds deploy to the `gh-pages` branch after `dev/tests/e2e/e2e_playground.mjs` passes (nothing to publish by hand). A new diagram type joins the playground in the same change (`blank.json`, `dev/playground/<type>.json`, `e2e_playground.mjs` `menuIds`, folder).

- **Staging (`stg`):** `.github/workflows/playground-stg.yml` builds the playground and examples and publishes to `/stg/` — https://khanhchungoc.github.io/ultimate-diagraming-skill/stg/
- **Production (`main`):** `.github/workflows/playground.yml` verifies signed-off `dev/samples/example-*.html` (`build_examples.py --check`, no regeneration), builds the playground, and publishes to `/` — https://khanhchungoc.github.io/ultimate-diagraming-skill/
