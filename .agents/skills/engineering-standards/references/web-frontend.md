# Web Frontend Engineering Standards

Load when designing, implementing, reviewing, or refactoring web frontend logic, state management, async flows, accessibility semantics, or browser security.

*Scope note: Visual layout, design tokens, CSS styling, and UI animations belong to dedicated design and motion skills (`ui-ux-pro-max`, `ui-styling`, `design-system`, `design`, `motion`). This reference covers frontend engineering correctness only.*

## State Ownership and Async Race Conditions

- **Keep one owner per piece of state.** Derive computed values during render rather than synchronizing duplicate state with effects. Do not copy props or server responses into local state unless managing an explicit, user-editable draft with a clear reset rule.
- **Guard against stale in-flight responses.** Rapid typing, filter switches, or route changes easily cause an older, slower request to resolve *after* a newer one and overwrite fresh UI. Cancel superseded requests with `AbortController` or ignore responses whose request ID/token no longer matches the latest request.
- **Handle all five data states explicitly.** Every async view must handle `loading`, `empty`, `error` (with recovery/retry), `partial/stale` (background refresh or partial failure), and `success`—never flash an empty-state illustration while data is still loading or leave an infinite spinner on error.
- **Sync navigable state with the URL.** Search filters, active tabs, sort order, and pagination that users expect to bookmark, share, or return to via the browser Back button belong in URL state, not ephemeral component memory.

## Accessibility Semantics (Engineering Layer)

- **Use native interactive elements.** Use `<button type="button|submit">` for actions and `<a href="...">` for navigation. Clickable `<div>` or `<span>` elements break keyboard activation (`Enter`/`Space`), focus order, screen-reader roles, and right-click/open-in-new-tab behavior.
- **Manage keyboard and focus in overlays.** Modals, drawers, popovers, and menus must move focus inside on open, keep Tab focus trapped while modal, close on `Escape`, and restore focus to the triggering element on close.
- **Wire programmatic form labels and errors.** Every input needs an explicit `<label htmlFor>` (or `aria-labelledby`), linked error/hint text via `aria-describedby`, and `aria-invalid` on failure. Never rely on `placeholder` as the only label.
- **Announce dynamic status changes.** Inline validation summaries, toast alerts, and async save/error results must use appropriate `role="alert"` / `aria-live="polite"` regions so assistive tech hears updates without stealing focus.

## Browser Security

- **Eliminate XSS sinks.** Never pass untrusted strings into `innerHTML`, `outerHTML`, `document.write`, `dangerouslySetInnerHTML`, or unescaped template HTML. If rich HTML rendering is required, sanitize with a vetted library (for example, DOMPurify) right at the render sink.
- **Validate dynamic URLs and redirects.** Reject `javascript:`, `vbscript:`, and unexpected `data:` schemes in user-supplied `href`/`src` attributes. Restrict post-login `next`/`returnTo` redirect targets to relative same-origin paths (blocking `//evil.com` protocol-relative bypasses).
- **Respect auth and CSRF boundaries.** Never rely on client-side checks for authorization, never embed private API keys in frontend bundles, and ensure cookie-authenticated mutations pair with backend CSRF defenses (`SameSite`, CSRF token, or Origin verification). Avoid storing long-lived sensitive tokens in `localStorage` when `HttpOnly` cookies are viable.

## Performance and Lifecycle Resilience

- **Avoid sequential request waterfalls.** Start independent data fetches in parallel (`Promise.all` / route-level loaders) instead of chaining fetch -> render child -> fetch child -> render grandchild.
- **Clean up side effects on unmount and dependency change.** Always tear down `addEventListener`, `setInterval`/`setTimeout`, `ResizeObserver`/`IntersectionObserver`, WebSockets, and store subscriptions to prevent memory leaks and post-unmount state errors.
- **Prevent double submission.** Disable or guard async submit buttons and form handlers while a mutation is in flight, and prevent Enter-key resubmission during processing.
- **Survive real-world content.** Test how components behave with very long unbroken strings (URLs, emails, German/Vietnamese labels), zero items, and hundreds of items—prevent horizontal overflow or clipping of primary buttons.

## Common Real-World Compromises

Raise these trade-offs explicitly before deciding:
- **Optimistic UI vs. wait-for-server:** Optimistic updates feel faster but complicate error rollback and conflict handling; prefer wait-for-server (with clear pending state) for destructive, financial, or server-validated mutations unless instant feedback is critical.
- **URL query state vs. local state for complex filters:** Putting deep nested filter builders in the URL can hit length/readability limits; keep primary filters in the URL or use saved server-side filter IDs.
- **Native `<dialog>` / platform primitives vs. full accessibility UI library:** Native primitives reduce bundle size, while battle-tested headless libraries (Radix, React Aria) handle edge-case focus/screen-reader bugs across browsers; match the app's existing stack.
