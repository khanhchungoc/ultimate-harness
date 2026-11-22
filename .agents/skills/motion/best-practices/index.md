# Animation best practices

## Choosing a tool

-   [CSS or Motion](css-or-motion.md): read this first when you add animation to a project.

## Platform-specific rules

-   [React](react.md)
-   [Vue](vue.md)
-   [Vanilla JS](motion.md)
-   [Base UI](base-ui.md)

## Universal rules (all platforms)

### Performance

#### Properties

Prefer transforms (`transform` or independent transforms like `x`, `y`, `scale`, `rotate`), `opacity`, `clipPath` and `filter` where possible as these are hardware accelerated. For continuous touch drags on multi-element containers, stick strictly to compositor-only `transform` and `opacity` (per-frame `filter` or CSS `mask-image` updates can trigger repaint/compositor thrash). When an element's size or position changes because of layout, use Motion's `layout` animations instead of animating `width`, `height`, `top` or `left`. 

#### Execution speed

Inside functions that run every animation frame (rAF callbacks, `useTransform` callbacks, pointer move callbacks, `onUpdate`, `frame.render` etc):

-   Avoid object allocation. Prefer mutation where safe.
-   Prefer `for` loops over `forEach` of `map`, unless function callback can be pre-allocated.
-   Avoid `Object.entries`, `Object.values`.

#### Animating via `transform` vs independent transforms

Motion can animate transforms either via `transform` or `x`, `y`, `scale` etc.

```javascript
animate(element, { transform: "scale(2)" })
animate(element, { scale: 2 })
```

```jsx
<motion.div animate={{ transform: "scale(2)" }} />
<motion.div animate={{ scale: 2 }} />
```

Both are hardware accelerated on HTML elements. Prefer independent transforms when:

-   Some transforms have different transition settings
-   Some transforms need to be passed in as motion values
-   Defining transforms via `style` prop
-   You have competing/composable transforms:

```javascript
animate(element, { x: 100 })

hover(() => {
    animate(element, { scale: 1.2 })
    return () => animate(element, { scale: 1 })
})
```

```jsx
<motion.div animate={{ x: 100 }} whileHover={{ scale: 1.2 }} />
```

Accelerated animations are de-optimised to the main thread when they use `onUpdate` (prop or transition option), `transformTemplate`, `type: "inertia"`, layout animations, on SVG elements, or when a transform motion value is set every frame (drag, `useMotionValue` streams). Don't change working code to avoid these, they still perform well.

#### will-change

When animating transforms, `opacity`, `clipPath` or `filter`, and it will de-opt according to rules above, set `will-change` on the animating properties so the browser promotes the element to its own compositor layer. Use it sparingly and remove it once the animation finishes.

When animating with CSS `animation` or a hardware-accelerated Motion animation (`transform`, `x`, `scale` etc), this is unnecessary — the layer is promoted automatically by the browser.

#### Mobile gesture performance trace check

Whenever creating or modifying interactive gestures or continuous animations (drawer pulls, swipe-back/dismiss, drag sheets, canvas pan/zoom), verify runtime performance before finishing:

1.  **Mid-tier mobile emulation:** Emulate mobile hardware via `chrome-devtools` MCP (e.g. `390x844` viewport, `deviceScaleFactor: 3`, mobile touch enabled) with `cpuThrottlingRate: 4` (4x CPU throttle).
2.  **Record a continuous drag trace:** Run `performance_start_trace`, execute a continuous 30-45 frame simulated touch drag/gesture, then run `performance_stop_trace`.
3.  **Zero forced reflows:** Inspect trace insights (`ForcedReflow`). Forced reflow duration inside move and pointer-release handlers must be **0 ms**. Never read layout geometry (`getComputedStyle()`, `getBoundingClientRect()`, `offsetWidth`/`offsetHeight`) inside gesture move/release loops when tracked pointer coordinates already provide geometry.
4.  **Compositor-only updates:** Restrict per-frame gesture updates to compositor-only `transform` and `opacity`; never mutate `filter` or CSS `mask-image` per frame on multi-element containers, and confirm zero layout thrash or subpixel jitter in the trace.

### Design

In general, prefer physics-based springs for physical motion such as `x`, `rotate` etc. Especially when it could be interrupted.

Non-numerical values won't use spring physics so you can use more predictable settings like `type: "spring", bounce: 0.2, visualDuration: 0.4`

Consider the kind of interface you are building. If a serious website like stock trading, don't use overshoot in your springs or easing curves. If it's a wedding site, you can use softer curves and slightly longer durations.

Keep UI animations short: about 150 to 300 ms for small elements, and up to about 500 ms for large surfaces.

Each animation should show a change of state, a relationship between elements or feedback to an action. Do not add animation only for decoration.

### Accessibility

Respect the reduced motion setting. In CSS, turn off or shorten movement inside `@media (prefers-reduced-motion: reduce)`. For Motion for React, see "Reduced motion" in [React](react.md).

### Generated code

Do not add comments, links, credits or tracking to the user's code unless they ask for them.

### API best practice

#### MotionValues

-   Never use `motionValue.onChange(update)` — always use `motionValue.on("change", update)`
