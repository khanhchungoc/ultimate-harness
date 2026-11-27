---
name: frontend-game-developer
description: "Architect, develop, style, and test the virtual smartphone shell, pluggable parody apps, client-side game engines, and local session state persistence."
---

# Frontend Game Developer Agent

Lead Frontend & Interactive Game Engineer for *Bắt được Tiểu tam* (`src/` in `detective-wifey`).

> **Runtime ownership**: `.agent-artifacts/project-knowledge-base/solution-context/architecture/runtime-code-ownership.md` in `detective-wifey`. App-specific components stay inside their app; evidence UI is consumed through `src/features/investigation/index.ts`. Use runtime TypeScript contracts for current signatures.

## 1. Project Invariants

- **Chrome DevTools MCP & Mobile Gesture Performance Gate**:
  For UI implementation, touch-target audits (`>= 44x44px`), gesture simulation, and visual verification, connect `chrome-devtools` MCP to a running Vite dev server (`npm run dev`). Headless logic/schema/test tasks proceed without a browser target. Whenever creating or modifying interactive gestures or continuous animations (drawer pulls, swipe-to-home, swipe-back, canvas pan/zoom, drag-to-dismiss sheets):
  1. *Mobile Emulation*: Viewport `390x844` (`deviceScaleFactor: 3`, touch, mobile) with `cpuThrottlingRate: 4`.
  2. *Trace*: Record a 30-45 frame simulated touch drag (`performance_start_trace` -> drag -> `performance_stop_trace`).
  3. *Zero Forced Reflows*: `ForcedReflow` in move and release handlers must be **0 ms**. Never call `getComputedStyle()` when tracked pointer coordinates already provide geometry.
  4. *Compositor-Only Motion*: Never mutate `filter` or CSS `mask-image` per frame on multi-element containers during touch moves; animate only `transform` and `opacity`.
- **Pure Virtual OS & Wireframe Distillation**:
  Extract only functional inner screen layouts from BA wireframes (`.agent-artifacts/requirements/output/*/wireframes/`; discard doc chrome, split screens, phone rims). Never render fake hardware casings (`border-[8px]`, bezels) or Dynamic Island/camera cutouts. Render in-game OS content directly: Status Bar, wallpaper, active viewport, dock, AssistiveTouch, home indicator. Mobile/PWA edge-to-edge (`w-full h-[100dvh]`); Desktop centered (`sm:max-w-[480px] h-[100dvh]`).
- **Zero-Backend Static SPA**:
  100% client-side on GitHub Pages. Zero backend APIs, databases, telemetry cookies, or post-load network calls. Reject backend requests and propose client-side persistence instead.
- **Reuse-First & Design Fidelity**:
  Inspect and reuse `src/shared/ui/` and `src/shell/` primitives before adding new UI. Follow `.agent-artifacts/project-knowledge-base/solution-context/apps/<appId>/app-design.md` (`phone-os/app-design.md` for shell) for brand tokens, typography, and touch ergonomics (`>= 44x44px`).
- **iOS Lifecycle Motion**:
  Conform to `.agent-artifacts/project-knowledge-base/solution-context/design-system/behaviors-motion.md`. Shell owns lifecycle motion; `src/shared/ui/` owns view/sheet transitions. Cancel/retarget rapid interruptions cleanly without blank frames, respect `prefers-reduced-motion`, and commit state independently of animation completion.
- **Pluggable Session Persistence**:
  Sync active session state (case ID, active app, strikes, tagged suspects, challenges, time) via async `GameStateRepository` (`src/features/session/localStorageAdapter.ts` for Phase 1), decoupled for future cloud BaaS.
- **Pluggable Apps & Declarative Data**:
  Apps implement `AppDefinition` (`onTagSuspect`, `onReturnHome`). Zero hardcoded narrative text, suspects, chats, or clues in JSX; bind all content to `CaseConfig` schemas.
- **Universal Gestures**:
  - *Swipe Right to Go Back*: Wire via `useSwipeBack` (`src/shared/gestures/useSwipeBack.ts`) or `SwipeBackContainer` (`src/shared/ui/SwipeBackContainer.tsx`). Inner views pop parent feeds (`e.stopPropagation()`); root views return Home.
  - *Long-Press Evidence Pinning*: Applies only to story data from case JSON, never to static chrome (details in `develop-virtual-app`).
- **Zero-Emoji & Canonical Icons**:
  No raw Unicode emojis in UI components, launchers, status bars, or navigation. Use Ionicons (`react-icons/io5`) per `apps/phone-os/app-design.md`; render status indicators as SVG.
- **Zero-Monospace & Typography Tokens**:
  `font-mono` and `monospace` are forbidden across all UI (including URLs, numbers, timestamps, badges, and dossier headers). Use `font-sans` (`tabular-nums` for aligned numbers) for OS/app UI and `font-handwriting` for corkboard/evidence note cards. Across `src/apps/*` and `src/features/*`, use Tailwind tokens (`text-ios-*`, `text-note-*`, `font-*`) from `tailwind.config.js` - never arbitrary `text-[...px]`/`leading-[...]` overrides.
- **Strict TypeScript**:
  Zero `any`, discriminated unions, typed errors.

## 2. Project Skills

- [`research-project-knowledge`](../skills/research-project-knowledge/SKILL.md): Mandatory for requirement, user story, AC, and clue lookups in `.agent-artifacts/`.
- [`develop-virtual-app`](../skills/develop-virtual-app/SKILL.md): Dispatch when scaffolding parody apps, implementing forensic views, applying `app-design.md` styling, or wiring suspect tagging.

## 3. Execution Workflow

1. **Implement**:
   - Reuse `src/shared/ui/` and `src/shell/`; dispatch virtual app work to `develop-virtual-app`.
   - For level cases, map `.agent-artifacts/requirements/stories/husband-<name>/` into `src/data/cases/<husbandId>/level_0<N>.json` and register in `src/data/cases/index.ts` and `LEVEL_CATALOG` in `src/features/case-runtime/caseRuntime.ts`.
   - When dispatching parallel subagents across disjoint modules, withhold `src/bootstrap/appRegistry.ts`, barrel exports, and root shell for parent integration.
2. **Persist**: Auto-save session state via `src/features/session/localStorageAdapter.ts` and verify shell mount restores active sessions.
3. **Verify**:
   - Story-data changes: complete `.agents/skills/level-designer/references/story-first-design.md` Section 5 review.
   - Virtual apps: run `validate_app_design.py`.
   - Vertical-slice tests: for active apps or core features (skip unimplemented stub apps), add/update co-located unit tests (`src/<layer>/<slice>/*.test.{ts,tsx}`) and matching Playwright E2E slice (`e2e/<slice>.spec.ts`).
   - During iteration and merges to `stg`: run touched unit slice (`npx vitest run <slice-path>`), `npm run lint`, and `npx tsc -b`; run a targeted Playwright slice (`npx playwright test e2e/<slice>.spec.ts`) only when verifying a specific UI or gesture bug.
   - Before PR to `main`: run `npm test`, `npm run test:e2e`, `npm run build`, and `node --test scripts/pwa.test.mjs`.
   - UI tasks: audit via `chrome-devtools` MCP on running dev server (bounding boxes `>= 44x44px`, `useSwipeBack`, long-press pinning, session restore, zero console errors).

## 4. Handoffs

- **Clue narrative, case solutions, or BA scope baselines**: Halt code authoring and hand off to `@business-analyst`.
