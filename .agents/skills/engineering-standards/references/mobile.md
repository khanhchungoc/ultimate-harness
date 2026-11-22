# Mobile Engineering Standards

Load when designing, implementing, reviewing, or refactoring iOS, Android, React Native, or Flutter mobile applications.

## Offline and Poor-Network Resilience

- **Assume networks drop mid-flight.** Mobile connections switch between Wi-Fi and cellular, hit tunnels, and stall on captive portals. Configure explicit request timeouts, cancel stale requests on navigation, and retry only safe/idempotent calls with bounded backoff.
- **Preserve unsent user input.** Never discard form entries, messages, or media selections when a submission fails offline or times out. Keep drafts persisted locally until the server confirms receipt, and surface a clear retry action.
- **Show honest connectivity and freshness states.** Distinguish offline/cached views from live errors and active loading—never trap users on an indefinite spinner when offline or silently display stale balances/statuses as live.

## App Lifecycle and State Restoration

- **Survive backgrounding and OS process kill.** Mobile OSes aggressively suspend and reclaim backgrounded apps. Never assume in-memory singletons, navigation params, or auth state remain hydrated across process death; restore critical navigation and form state from durable state or re-bootstrap cleanly.
- **Handle interrupted flows and cold-start deep links.** Incoming phone calls, biometric prompts, OS permission dialogs, push notifications, and universal/app links can launch directly into a deep screen from a cold start (including while logged out). Route through a deterministic auth/bootstrap gate and resume the target destination afterward.
- **Clean up listeners on lifecycle transitions.** Unsubscribe screen listeners, cancel timers, and guard async callbacks when a view unmounts or backgrounds so late responses do not crash or mutate torn-down views.

## Permissions and Secure Storage

- **Request permissions just-in-time with clear rationale.** Ask for camera, location, notifications, or contacts only when the user triggers the feature that needs them—never dump a wall of permission prompts on first launch.
- **Handle permanent denial gracefully.** On both iOS and Android ("Don't ask again"), re-requesting a permanently denied permission silently fails without showing a dialog. Detect permanent denial, explain why the feature is unavailable, and offer a direct button to OS App Settings—while keeping the rest of the app usable.
- **Use OS hardware-backed secure storage for secrets.** Store auth tokens, refresh tokens, session keys, and sensitive user PII in iOS Keychain or Android Keystore/EncryptedSharedPreferences—never in plain `UserDefaults`, `SharedPreferences`, `AsyncStorage`, unencrypted SQLite, or debug logs. Clear secure storage and sensitive disk caches on logout (and note iOS Keychain persists across app reinstalls unless cleared on first launch).

## Device and Interaction Constraints

- **Respect safe areas and system bars.** Keep interactive controls and critical content clear of notches, Dynamic Island, rounded corners, status bars, and bottom gesture indicators across devices.
- **Keep keyboard-covered inputs and actions reachable.** Wrap forms in keyboard-aware scrollable containers so the active field and primary submit button remain visible and tappable when the soft keyboard opens, and allow dismissing the keyboard cleanly.
- **Support system dynamic font scaling.** Users enable large accessibility text sizes; avoid fixed-height containers that clip scaled labels, allow text wrapping where needed, and verify layouts at large font scales and narrow screen widths.
- **Maintain reliable touch ergonomics.** Keep interactive hit targets at least `44x44 pt` (iOS) / `48x48 dp` (Android) with enough spacing to avoid mis-taps, and verify orientation or split-screen changes do not lose screen state.

## Main-Thread, Battery, and Storage Hygiene

- **Keep heavy work off the UI/main thread.** Move large JSON parsing, database queries, encryption, file I/O, and image decoding/resizing onto background threads/isolates to prevent dropped frames, frozen gestures, and Android ANRs.
- **Release power-hungry hardware on background.** Stop camera sessions, high-accuracy GPS polling, continuous sensors, animations, and active WebSockets when the app backgrounds unless an explicit, justified foreground/background service requires them.
- **Bound local disk and image caches.** Set explicit size/TTL limits and eviction policies on image, media, and offline data caches so the app does not bloat device storage or fail under low-disk conditions.

## Common Real-World Compromises

Raise these trade-offs explicitly before deciding:
- **Read-only offline cache vs. full offline write-sync queue:** Offline mutation queues require conflict resolution, schema versioning, and partial-failure UX. Prefer preserving unsent drafts + read-only caching unless true offline editing is a core requirement.
- **Locked orientation on specialized screens:** Locking portrait on a camera scanner or landscape on a full-screen video player is reasonable; avoid locking general content/form screens without a clear reason (especially on tablets/foldables).
- **Coarse location or on-demand fetch vs. continuous background GPS:** Prefer significant-change or foreground-only location to protect battery life and avoid strict App Store / Play Store background-location review hurdles.
