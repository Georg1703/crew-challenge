# Design system

The app's look is **not final**: the current theme is a deliberately plain placeholder. What is
final is the *structure*, so the look can change many times while every screen stays consistent.

See it live: run the frontend and open `/design` (development only). It shows every token and
component, in light and dark.

## The three rules

1. **Tokens are the only place a look is defined** (`frontend/src/styles/tokens.css`).
2. **Screens are built only from `shared/ui` components** and layout CSS that uses tokens.
3. **Motion uses named presets** from `shared/motion`, never ad-hoc numbers.

`make check` enforces all three (see "Guardrails").

## Tokens

Two layers in `tokens.css`:

| Layer | Names | Used by |
|---|---|---|
| Primitives | `--palette-*` (raw colors) | Only the semantic layer below |
| Semantic | `--color-*`, `--text-*`, `--weight-*`, `--leading-*`, `--space-*`, `--radius-*`, `--shadow-*`, `--z-*`, `--duration-*`, `--ease-*`, `--tap-min`, `--tabbar-height`, `--content-max-width` | Components and screens |

- Components never use `--palette-*`. To restyle the app, re-map semantic tokens to other
  primitives (or change primitives).
- **Dark mode** re-maps semantic colors only. It follows the phone's setting; `data-theme="light"`
  or `"dark"` on `<html>` forces one. The two dark blocks in `tokens.css` must stay identical (a
  test checks it).
- Name tokens by **role** (`--color-danger`), never by look (`--color-red`).
- A new token needs a reason: prefer an existing one. Add it to `tokens.css` and, for colors, to
  `src/design/tokens.ts` so it shows on `/design`.

## Components (`frontend/src/shared/ui`)

| Component | Use for |
|---|---|
| `Screen`, `Stack` | Every route's layout (safe areas, tab bar space, max width) and vertical spacing |
| `Button` | Every action. Variants: primary, secondary, ghost, danger. States: loading, disabled |
| `TextField` | Every text input, with label, hint and error wired for screen readers |
| `Card` | A group of related content on a surface |
| `Sheet` | Bottom-sheet dialogs (forms, details, share) |
| `Segmented` | A small set of exclusive options (language, theme) |
| `Badge` | Short status labels |
| `Avatar` | A member (initials + color from `avatar_seed`) |
| `Toast` (`useToast`) | Short feedback after an action |
| `Skeleton`, `Spinner` | Loading content (skeleton) and loading actions or whole pages (spinner) |
| `TabBar`, `Icon` | Main navigation; the shared icon set |

Rules:
- A feature needs something new? Add or extend a component in `shared/ui` (with all its states),
  show it on `/design`, then use it. Never style a one-off button inside a feature.
- Every component handles its states: default, pressed, focus-visible, disabled, loading and
  error where relevant. Touch targets are at least `--tap-min` (44px).
- Every screen designs its loading, empty and error states.

## Motion

| Preset | Feel | Use for |
|---|---|---|
| `snappy` | Fast, firm | Buttons, toggles, small feedback |
| `bouncy` | Playful overshoot | Celebrations, items popping in |
| `gentle` | Soft, slower | Sheets, page and large-surface transitions |

- Import from `@/shared/motion`: `motion`, `AnimatePresence`, `useSpring(name)`, `variants`
  (`popIn`, `fadeUp`), `staggerStep`, `pressScale`.
- Animate only `transform` and `opacity`.
- `useSpring()` returns a short fade when the user prefers reduced motion; `MotionConfig` in the
  app providers does the same for every animation.
- CSS transitions use `--duration-*` and `--ease-*` tokens.

## Writing

- Every visible string comes from `src/i18n/ro.json` and `en.json` (same keys in both).
- Plain, warm, short. Address the user as "tu" in Romanian. Buttons say what happens
  ("Copy link", not "OK").
- Errors say what happened and what to do next.

## Guardrails (run by `make check`)

| Rule | Tool |
|---|---|
| No hex, rgb, hsl or named colors outside `tokens.css` | Stylelint `color-no-hex`, `color-named`, `function-disallowed-list` |
| Colors, spacing, font sizes, radii, shadows, z-index must use `var(--...)` | Stylelint `declaration-strict-value` |
| No raw durations in `transition` or `animation` | Stylelint `declaration-property-value-disallowed-list` |
| No inline `style` props (except `shared/ui` and `/design`) | ESLint `react/forbid-dom-props` |
| No user-visible text literals in JSX | ESLint `react/jsx-no-literals` |
| Animation only via `@/shared/motion` | ESLint `no-restricted-imports` |
| Dark blocks identical, `/design` colors exist | Vitest `src/design/tokens.test.ts` |

## Changing the look later

1. Edit `tokens.css` (palette, fonts, radii, shadows, motion durations) and, for feel,
   `shared/motion/presets.ts`.
2. Restyle components in `shared/ui` if their shape changes.
3. Check `/design` in light and dark, then the real screens.

Screens should not need changes for a new look. If one does, the rule it broke belongs in this
document.
