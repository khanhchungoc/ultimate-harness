## Motion

- **Motion skill, every task.** For any task that touches animation, transitions, or UI motion (including actions that add or change interactive behaviour), invoke the global `motion` skill first and follow it. Repo principle: **morph, not fade**. An element that changes state, position or shape animates from its old geometry to its new one (see `morphRect`, `morphRing`, `ghostMorph` in `assets/shell/shell.js`); never cross-fade or fade in/out as a substitute.

## Coding principles

- **Maintainable and scalable.** Code must stay easy to maintain and scale to every diagram type and size, from a handful of nodes to thousands. A change that works for one type or small diagram but breaks or slows down another is not done.
- **Reuse and DRY.** Search `assets/components`, `assets/shell`, and `scripts/` first, and extend an existing helper or component before adding new code. Share across diagram types through `assets/components` and `assets/shell` (extract on the third copy, never if sharing would couple two types).
- **Single source of truth (SSOT).** Tokens live in `assets/tokens` and `scripts/tokens.py`, layout in `scripts/layout_engine.py`, the file format in `scripts/disk_format.py`, and the type list in `SUPPORTED_TYPES`. Never copy these into a type, component, or playground, and never hardcode colors, sizes, or fonts.
- **Vertical slices.** One diagram type is one complete slice: its folder, `blank.json`, playground entry, example, checker or e2e test, and docs in the same change.
- **SOLID, kept light.** The shell and layout engine are open for extension and closed for modification: a new type plugs in through a contract, and core code is not edited per type. Keep component APIs small. Prefer small modules and plain functions; use classes only for real state or polymorphism, not as a rule.
- **Contract first.** The disk format is the public API. Changing it needs a migration and a golden test (`dev/tests/unit/check_golden.py`).
- **Deterministic.** The same input must always give the same layout and output: no randomness, no time-based values.
- **Validate at the edge.** Check input once at the boundary and fail loudly, then trust it inside.
- **Verify before done.** Run each slice's checker or e2e test under `dev/`, and check light and dark themes and contrast.
- **No new dependencies** without a stated reason; the skill must stay portable.

## Implementation plans

Implementation plans live in `dev/plans/`. Once all phases of a plan are complete, mark the plan as completed and move it into `dev/plans/archive/`.

## Playground (GitHub Pages)

The playground (every diagram type, blank, with a type switcher) deploys itself from `main` via `.github/workflows/playground.yml`, after `dev/tests/e2e/e2e_playground.mjs` passes. Nothing to publish by hand. A new diagram type joins it in the same change (switcher entry, `blank.json`, folder).

Playground URL: https://khanhchungoc.github.io/ultimate-diagraming-skill/
