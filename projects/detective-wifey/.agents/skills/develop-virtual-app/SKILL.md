---
name: develop-virtual-app
description: "Scaffold, implement, style, and test pluggable parody virtual applications conforming to the emulated phone shell AppDefinition contract, declarative case schemas, forensic suspect tagging, and app-design.md specifications."
---

# Develop Virtual App

> **Current runtime ownership and imports** (in `detective-wifey`): `.agent-artifacts/project-knowledge-base/solution-context/architecture/runtime-code-ownership.md`. App-specific components stay inside their app; evidence UI is consumed through `src/features/investigation/index.ts`. Use runtime TypeScript contracts for current signatures.

- Implements modular, client-side virtual applications mounted on the emulated smartphone container for the *Jealous Wife Detective Game*.
- Enforces strict adherence to individual `app-design.md` branding tokens, touch target ergonomics (>= 44x44px), the `AppDefinition` registry contract, and declarative clue wiring.

## References

Query these files in the `detective-wifey` repo on demand:
- **Authoritative Architecture (SAD)**: `.agent-artifacts/project-knowledge-base/solution-context/architecture/apps-features-architecture.md` - Shell container, app grid invariant, and engine interactions.
- **Micro-App Design Specifications (SSOT for UI/UX)** under `.agent-artifacts/project-knowledge-base/solution-context/apps/`:
  - Zola (Internet Messaging): `internet-messaging/app-design.md` | `internet-messaging/features.md`
  - VietPay (Banking): `banking/app-design.md` | `banking/features.md`
  - Shopoo (E-Commerce): `ecommerce/app-design.md` | `ecommerce/features.md`
  - Grap (Ride Hailing): `ride-hailing/app-design.md` | `ride-hailing/features.md`
  - NetSurf (Web Browser): `web-browser/app-design.md` | `web-browser/features.md`
  - GeeMail (Email): `email/app-design.md` | `email/features.md`
  - InkedLin (Professional Network): `professional-network/app-design.md` | `professional-network/features.md`
  - Tim (Team Collaboration): `team-collaboration/app-design.md` | `team-collaboration/features.md`
  - Phone & Messages (Comms): `phone-os/phone/app-design.md`, `phone-os/messages/app-design.md`
  - Photos (Media Gallery): `phone-os/photos/app-design.md` | `phone-os/photos/features.md`
  - Husband's Notes: `personal-notes/app-design.md` | `personal-notes/features.md`
  - Wife's Notebook: `phone-os/wife-notebook/app-design.md` | `phone-os/wife-notebook/features.md`
- **Data & Contract Schemas**: [references/app-contracts.md](references/app-contracts.md) - TypeScript interfaces for `AppDefinition`, `CaseData`, and session state.
- **Component Boilerplate**: [assets/app-component.template.tsx](assets/app-component.template.tsx) - Starter React component.

## Prerequisites & Inputs

> [!IMPORTANT]
> **Stop & Ask on Ambiguity**: If the target `appId`, clue schema, or UI design specification is ambiguous: **STOP IMMEDIATELY**. Ask the user for clarification with structured options (2-4 per turn) and a recommendation.

- **Target App ID**: Registered `AppId` in `src/shared/contracts/app-contracts.ts` (e.g., `zola`, `vietpay`, `poshee`, `grap`, `netsurf`, `photos`, `comms`, `husband_notes`).
- **Design & Component SSOT**: Target app's canonical `app-design.md` and shared primitives under `src/shared/ui/`, `src/shell/`. Always reuse existing assets first.
- **Clue Mapping**: Target clue IDs verified against level design specs (`husband-<name>/level-XX.md`) or `caseData.appsData`.

## Procedure

### Step 1: Design & Specification Intake (Mandatory App Design & Reuse Gate)
1. Read the target app's `app-design.md` file using `view_file`. Extract:
   - Primary and secondary brand color hex codes.
   - Parody identity and trademark defense guidelines (e.g., avoid real-world app blue/green palettes).
   - Canonical icon pack mapping from `apps/phone-os/app-design.md` Section 2.4 (Ionicons `react-icons/io5`). Strictly enforce zero Unicode emojis.
   - Touch target dimensions (>= 44x44px) and row height constraints.
   - Screen hierarchy and layout wireframes.
2. Read the app's `features.md` to identify forensic capabilities (e.g., chat search, hidden albums, ride history).
3. Audit `src/shared/ui/` to map existing shared components against the app-design layout wireframes. Never create new components if an existing primitive can be reused or extended.
4. When inspecting wireframes, extract strictly the inner micro-app view hierarchy conforming to the Pure OS invariant in [frontend-game-developer.md](../../agents/frontend-game-developer.md); discard documentation scaffolding and simulated browser chrome.

### Step 2: Component Scaffolding & Registry Setup
1. Instantiate [assets/app-component.template.tsx](assets/app-component.template.tsx) into `src/apps/<appId>/<AppName>App.tsx`.
2. Configure the `AppDefinition` export in `src/apps/<appId>/index.ts`:
   - `appId`: Strict literal matching `AppId`.
   - `displayName`: Parody app name from `app-design.md`.
   - `themeColor`: Brand hex code.
   - `iconAsset`: Path to optimized SVG icon or canonical Ionicons icon identifier (strictly zero Unicode emojis).
   - `component`: The React component.
3. Register the new app export in `src/bootstrap/appRegistry.ts`.

### Step 3: Implement Forensics, Interactivity & Navigation
1. Implement the header with a back button (`min-h-[44px] min-w-[44px]`) invoking `onReturnHome` or returning to the top list view.
2. Implement feed/list and detail/inspection views.
3. Ensure all list rows and tap targets satisfy >= 44x44px minimum clickable bounds.
4. Wire universal **Swipe Right to Go Back** via `useSwipeBack` (`src/shared/gestures/useSwipeBack.ts`) or `SwipeBackContainer` (`src/shared/ui/SwipeBackContainer.tsx`): detail views must pop back to list view with `e.stopPropagation()`, and root views must navigate to `onReturnHome()`.

### Step 4: Wire Suspect Tagging & Declarative Clues (Universal Long-Press Invariant)
1. **Story Narrative Data Only**:
   - Wrap legitimate story narrative elements loaded dynamically from `caseData.appsData?.[appId]` (chat bubbles, call records, SMS texts, bank transaction memos, order receipts, notes, private photos) in `<StoryEvidenceTarget item={{ title, subtitle, snippet, suspectToTag }} onTriggerEvidence={setEvidenceItem}>`.
   - On 380ms long-press, mount `<UniversalEvidenceModal>` providing a blurred snapshot preview and a confirmation button to pin into the Wife's Notebook via `onTagSuspect(suspectName, appId)`.
2. **Prohibition on App Chrome & Structural Elements**:
   - Never wrap navigation headers, back buttons, tabs, search inputs, contact action rows ("Cloud của tôi", "Lời mời kết bạn"), or settings buttons in `StoryEvidenceTarget`. They must respond exclusively to standard clicks/taps with zero evidence overlays.
3. **Strict Zero-Button Pin Invariant**:
   - Permanent "Ghim" or physical Pin buttons (`<button>.*Ghim.*</button>`) are strictly forbidden across all app screens, feeds, and modals. Clues can ONLY be pinned via the long-press modal.
4. **Declarative Ingestion & Benign Filler**:
   - Consume dynamic case data exclusively from `caseData.appsData?.[appId]`.
   - If no clues are present for this app in the current case, render realistic benign filler content (parody memes, spam notifications, family chats) to prevent process-of-elimination spoilers.

### Step 5: Verification & Contract Audit Gate
For story-data changes, apply `.agents/skills/level-designer/references/story-first-design.md` Section 5 as part of this gate.

Execute the following verification commands in order. All checks must pass with zero errors before reporting completion:
1. Run the companion design and contract verification script:
   ```bash
   python3 .agents/skills/develop-virtual-app/scripts/validate_app_design.py --app-id <appId> --component src/apps/<appId>/<AppName>App.tsx
   ```
2. Add or update the app's vertical-slice tests (skip for unimplemented stub apps):
   - Co-located unit tests in `src/apps/<appId>/*.test.{ts,tsx}`
   - Matching browser E2E slice in `e2e/<appId>.spec.ts` covering navigation and 380ms long-press evidence pinning
3. Run fast targeted slice checks during iteration:
   ```bash
   npx tsc -b
   npx vitest run src/apps/<appId>
   npx playwright test e2e/<appId>.spec.ts
   ```
4. Before PR to `main`, run full verification (`npm test`, `npm run test:e2e`, `npm run build`, `node --test scripts/pwa.test.mjs`).
5. Inspect touch targets (>= 44x44px) and transition latency (< 100ms).

## Conditional Branching & Fallbacks

- **Branch: If App or Folder is Locked (`lockChallengeId`)**:
  - Check if `unlockedChallenges.has(challengeId)`.
  - If locked, render the polymorphic lock interceptor overlay (4-digit numeric PIN pad or security question challenge) or invoke `onRequestUnlock(challengeId)`.
  - Dispatch failed attempts to the global Suspicion Engine.
- **Branch: If Declarative Data is Empty for Current Level**:
  - Render benign, realistic parody filler. Never crash with `undefined` property errors.
- **Error: If Contract Validation Fails**:
  - Inspect output of `validate_app_design.py`. Fix missing handlers (`onReturnHome`, `onTagSuspect`) or unaligned color tokens before proceeding.

## Deliverables & Consumer Soundness

- **Primary Consumer**: TypeScript compiler, Vite bundler, React runtime.
- **Artifacts**:
  - `src/apps/<appId>/<AppName>App.tsx` (Component implementation).
  - `src/apps/<appId>/index.ts` (Exporting `AppDefinition`).
  - `src/bootstrap/appRegistry.ts` (App registry entry).
- **Quality Gates**:
  - 100% compliant with colors and wireframes in `app-design.md`.
  - Zero hardcoded clue narratives.
  - Strict TypeScript compliance (zero `any`, full type safety across `VirtualAppProps`).
  - SOLID modularity: Subcomponents separated by responsibility (Header, List, Detail, LockGate).
  - Passes `validate_app_design.py` with zero contract errors.

## Anti-Patterns & Negative Constraints

- **Never bypass `app-design.md`**: Do not invent arbitrary color schemes, fonts, or layouts without checking the authoritative `app-design.md` first.
- **Never hardcode clues or suspect names**: Clue data must come from declarative `caseData` schemas.
- **Never mutate the home screen shell directly**: Pluggable apps must remain strictly decoupled and mount via the registry.
- **Never omit touch targets**: Every interactive button, list row, or tab must have minimum dimensions of 44x44px.
- **Never make network calls**: Virtual apps execute 100% client-side; never invoke `fetch()` or external APIs.
- **Never use `any` types or bypass prop validation**: Strongly type all internal component state and props.
- **Never write monolithic single-file apps**: Decompose apps into subcomponents with clear single responsibilities.
- **Never create redundant UI primitives**: If a header, back button, modal sheet, lock pad, or suspect tag button already exists in `src/shared/ui/`, reuse or compose it instead of writing a duplicate version inside the app.
- **Never use raw Unicode emojis for UI icons or buttons**: Strictly render vector SVG icons from the canonical icon pack (Ionicons `react-icons/io5`) defined in `phone-os/app-design.md`.
- **Never port wireframe documentation chrome or wrap apps in fake chassis frames**: Micro-apps mount directly within the Pure OS viewport defined in [frontend-game-developer.md](../../agents/frontend-game-developer.md); never copy multi-view comparison headers, simulated browser toolbars, or outer hardware casings.
