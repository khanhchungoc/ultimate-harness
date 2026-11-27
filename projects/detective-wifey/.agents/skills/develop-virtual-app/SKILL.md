---
name: develop-virtual-app
description: "Scaffold, implement, style, and test pluggable parody virtual applications conforming to the emulated phone shell AppDefinition contract, declarative case schemas, forensic suspect tagging, and app-design.md specifications."
---

# Develop Virtual App

Implements modular, client-side parody virtual apps mounted on the emulated smartphone shell. Operates under [frontend-game-developer.md](../../agents/frontend-game-developer.md) for OS-wide invariants (Pure OS viewport, zero-backend, zero-emoji/Ionicons, typography tokens, `>= 44x44px` touch targets, `useSwipeBack`, `src/shared/ui/` reuse, strict TypeScript, and test cadence).

## References

Query these files in the `detective-wifey` repo on demand:
- **Authoritative Architecture (SAD)**: `.agent-artifacts/project-knowledge-base/solution-context/architecture/apps-features-architecture.md`
- **Micro-App Design Specs (SSOT)** under `.agent-artifacts/project-knowledge-base/solution-context/apps/`:
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
- **Data & Contract Schemas**: [references/app-contracts.md](references/app-contracts.md)
- **Component Boilerplate**: [assets/app-component.template.tsx](assets/app-component.template.tsx)

## Prerequisites & Inputs

> [!IMPORTANT]
> **Stop & Ask on Ambiguity**: If the target `appId`, clue schema, or UI design specification is ambiguous, stop and ask the user with structured options (2-4 per turn) and a recommendation.

- **Target App ID**: Registered `AppId` in `src/shared/contracts/app-contracts.ts` (e.g., `zola`, `vietpay`, `poshee`, `grap`, `netsurf`, `photos`, `comms`, `husband_notes`).
- **Clue Mapping**: Target clue IDs verified against level design specs (`husband-<name>/level-XX.md`) or `caseData.appsData`.

## Procedure

### Step 1: Design & Specification Intake
1. Read the target app's `app-design.md` with `read_file`. Extract brand color hex codes, parody identity and trademark defense rules (e.g., avoid real-world app blue/green palettes), row height constraints, and screen hierarchy.
2. Read the app's `features.md` for forensic capabilities (e.g., chat search, hidden albums, ride history).
3. Audit `src/shared/ui/` to reuse or extend existing primitives before writing new ones.

### Step 2: Component Scaffolding & Registry Setup
1. Instantiate [assets/app-component.template.tsx](assets/app-component.template.tsx) into `src/apps/<appId>/<AppName>App.tsx`. Decompose into focused subcomponents (Header, List, Detail, LockGate) rather than a monolith.
2. Export `AppDefinition` in `src/apps/<appId>/index.ts`:
   - `appId`: Strict literal matching `AppId`.
   - `displayName`: Parody app name from `app-design.md`.
   - `themeColor`: Brand hex code.
   - `iconAsset`: Path to optimized SVG icon or canonical Ionicons identifier.
   - `component`: The React component.
3. Register the export in `src/bootstrap/appRegistry.ts`. Never mutate the home screen shell directly.

### Step 3: Interactivity & Navigation
1. Render the header back button (`min-h-[44px] min-w-[44px]`) invoking `onReturnHome` or popping to the list view.
2. Implement feed/list and detail/inspection views with `useSwipeBack` / `SwipeBackContainer` (detail views pop to list with `e.stopPropagation()`; root views call `onReturnHome()`).

### Step 4: Suspect Tagging & Declarative Clues (Universal Long-Press Invariant)
1. **Story Narrative Data Only**:
   - Wrap dynamic narrative elements from `caseData.appsData?.[appId]` (chat bubbles, call records, SMS texts, bank transaction memos, order receipts, notes, private photos) in `<StoryEvidenceTarget item={{ title, subtitle, snippet, suspectToTag }} onTriggerEvidence={setEvidenceItem}>`.
   - On 380ms long-press, mount `<UniversalEvidenceModal>` showing a blurred snapshot preview and confirmation button to pin into Wife's Notebook via `onTagSuspect(suspectName, appId)`.
2. **Prohibition on App Chrome & Structural Elements**:
   - Never wrap navigation headers, back buttons, tabs, search inputs, contact action rows ("Cloud của tôi", "Lời mời kết bạn"), or settings buttons in `StoryEvidenceTarget`. They must respond only to standard clicks/taps with zero evidence overlays.
3. **Strict Zero-Button Pin Invariant**:
   - Permanent "Ghim" or physical Pin buttons (`<button>.*Ghim.*</button>`) are strictly forbidden across all app screens, feeds, and modals. Clues pin ONLY via the long-press modal.
4. **Declarative Ingestion & Benign Filler**:
   - Consume dynamic case data exclusively from `caseData.appsData?.[appId]`.
   - If no clues exist for this app in the current case, render realistic benign filler (parody memes, spam notifications, family chats) to prevent process-of-elimination spoilers.

### Step 5: Verification & Contract Audit
1. For story-data changes, complete `.agents/skills/level-designer/references/story-first-design.md` Section 5 review.
2. Run the app design and contract validator:
   ```bash
   python .agents/skills/develop-virtual-app/scripts/validate_app_design.py --app-id <appId> --component src/apps/<appId>/<AppName>App.tsx
   ```
3. Add or update the app's vertical-slice tests (skip unimplemented stub apps):
   - Unit tests: `src/apps/<appId>/*.test.{ts,tsx}`
   - E2E slice: `e2e/<appId>.spec.ts` covering navigation and 380ms long-press evidence pinning
4. Run the test cadence from `frontend-game-developer.md` and check touch targets (`>= 44x44px`) and transition latency (`< 100ms`).

## Conditional Branching & Fallbacks

- **Locked App or Folder (`lockChallengeId`)**: Check `unlockedChallenges.has(challengeId)`. If locked, render the polymorphic lock interceptor overlay (4-digit PIN pad or security question) or invoke `onRequestUnlock(challengeId)`, dispatching failed attempts to the global Suspicion Engine.
- **Empty Declarative Data**: Render benign parody filler; never crash on `undefined` properties.
- **Contract Validation Failure**: Inspect `validate_app_design.py` output and fix missing handlers (`onReturnHome`, `onTagSuspect`) or misaligned color tokens before proceeding.
