# Design system

The look of Crew Challenges is defined here and in code. Read this page before any UI work.
`make check` enforces the rules marked (enforced).

- Tokens: `frontend/src/styles/tokens.css` (the only place a color, size or font is defined)
- Components: `frontend/src/shared/ui` (the only place a button, field or sheet is styled)
- Motion presets: `frontend/src/shared/motion`
- Live page: run the frontend and open `/design` (development only), in light and dark.

## Principles

1. **The proof is the picture.** Photos and videos from the crew are the only imagery. No
   illustrations, mascots, trees, confetti or decorative graphics in v1.
2. **One job per screen.** One title, one primary button. Everything else is quieter.
3. **State over decoration.** Done, to do, missed and uploading must be readable at a glance, by
   color and by shape (a check, a ring, a pill), never by color alone.
4. **Say it once, plainly.** Romanian first, English second. No slogans.

## Writing

- One title per screen (`Screen title`, style title-l). It names the screen or asks the question
  the screen answers ("Provocari", "Ce bifezi?").
- No tagline under the title. Add one line of body text only when it carries a fact the person
  needs: a deadline, a count, what happens next.
- No small uppercase labels above headings, no colored or italic words inside a title.
- Sentence case everywhere, including buttons and tabs.
- Buttons say exactly what happens ("Copy link", "Join the crew"). The result uses the same verb
  ("Link copied").
- Numbers beat adjectives: "6 hours left", "6/7 days", "1.1 GB of 3.1 GB".
- Errors say what went wrong and what to do next, without apologizing.
- Empty states say what will appear and how to add the first item.
- Every string comes from `src/i18n/ro.json` and `en.json` (same keys). Address the user as "tu".

## Tokens

Two layers in `tokens.css`: primitives (`--palette-*`, raw values) and semantic tokens. Components
and screens use only semantic tokens (enforced). Dark mode re-maps semantic colors and shadows;
the two dark blocks must stay identical (enforced by a test). Name tokens by role, never by look.
A new token needs a reason: add it to `tokens.css` and, for colors and sizes, to
`src/design/tokens.ts` so it shows on `/design`.

### Color

| Design name | Token | Use |
|---|---|---|
| bg | `--color-bg` | Screen background |
| surface | `--color-surface` | Cards, list groups, sheets, tab bar, inputs |
| surface-sunken | `--color-surface-sunken` | Segmented track, disabled fields, icon tiles |
| line | `--color-border` | Borders and dividers |
| ink | `--color-text` | Titles and body text |
| ink-muted | `--color-text-muted` | Secondary lines, hints, labels, inactive tabs |
| ink-disabled | `--color-text-disabled` | Placeholders and disabled labels only, never information |
| primary | `--color-accent` (+ `-pressed`, `-soft`), `--color-on-accent` | The one main action per screen; `-soft` highlights at most one card |
| success | `--color-success`, `--color-success-soft` | Done, checked in, the active tab |
| warning | `--color-warning`, `--color-warning-soft` | Attention: offline, paused, large file |
| danger | `--color-danger`, `--color-danger-soft` | Errors, missed days, destructive actions |
| focus | `--color-focus-ring` | Keyboard focus outline (2px) |
| overlay | `--color-overlay` | Dim layer behind sheets |
| avatar-1..5 | `--color-avatar-1` .. `-5`, `--color-on-avatar` | Member colors, white initials |
| code | `--color-code-bg`, `--color-code-fg` | QR codes: dark on white in both themes |

Every text color reaches 4.5:1 on its background in both themes (enforced by
`src/design/tokens.test.ts`). Status colors are never decoration.

### Type

One family, **Nunito Sans** (self-hosted from `@fontsource-variable/nunito-sans`, Latin files
precached), weights `--weight-regular` (400) and `--weight-bold` (700) only.

| Style | Tokens | Use |
|---|---|---|
| title-l | `--text-title-l` 28 / `--leading-title-l` 34, bold, `--tracking-title` | The one screen title (`h1`) |
| title-m | `--text-title-m` 20 / 26, bold | Sheet titles, section titles (`h2`) |
| title-s | `--text-title-s` 17 / 22, bold | Card titles (`h3`) |
| body | `--text-body` 15 / 22 | Running text, inputs |
| body-strong | `--text-body` 15 / 22, bold | Button labels, list row titles |
| small | `--text-small` 13 / 18 | Secondary lines, hints, metadata |
| caption | `--text-caption` 12 / 16, bold | Field labels, pills, tab labels |
| number | `--text-number` 32 / 36, bold, tabular | Stat figures |

`font-family`, `font-size`, `font-weight` and `line-height` take tokens only (enforced).

### Shape, space, depth, size

- Radius: `--radius-md` 12px for buttons and inputs (about 23% of a 52px button),
  `--radius-lg` 16px for cards and lists, `--radius-xl` 24px for sheet tops, `--radius-sm` 8px for
  small cells and thumbnails, `--radius-full` for avatars and pills. No other values (enforced).
- Space: 4px grid, `--space-1` .. `--space-12`. Screen gutter `--space-5`, sections `--space-6`
  apart, card padding `--space-4` (enforced for margin, padding and gap).
- Depth: `--shadow-card` on cards and lists, `--shadow-sheet` on sheets, toasts and floating
  banners. Nothing else casts a shadow. Dark cards rely on their border.
- Sizes: `--tap-min` 44px (every control), `--button-height` 52px, `--button-height-sm` 44px,
  `--input-height` 48px, `--avatar-sm/md/lg` 28/40/64px, `--tabbar-height` 64px.

## Components (`frontend/src/shared/ui`)

Screens are built only from these plus layout CSS that uses tokens. In `src/features` the raw
`<button>`, `<input>`, `<textarea>`, `<select>` and `<dialog>` elements are not allowed
(enforced): use the components. Every export of `shared/ui/index.ts` is listed here and shown on
`/design` (enforced by `src/design/designSystem.test.ts`).

| Component | Use for |
|---|---|
| `Screen`, `Stack` | Every route's layout (safe areas, tab bar space, max width, the one title) and vertical spacing |
| `Button` | Every action. `primary` (one per screen), `secondary`, `ghost` (text action), `danger` (destructive, never primary). `size="lg"` (52px) for main actions, `md` (44px) inside cards. States: loading, disabled |
| `TextField` | Every text input: label above, hint or error below, wired for screen readers |
| `Card` | A group of related content. `tone="accent"` highlights the one thing that needs the user |
| `List`, `ListRow`, `IconTile` | Members, invites, settings: rows inside one surface. A row has a leading avatar or icon tile, a title, one secondary line and at most one trailing item. `to` makes the whole row a link, `onClick` a button; `current` marks the chosen row |
| `StatusPill` | Short status: `neutral`, `accent` (to do), `success` (done, with a check), `warning`, `danger` |
| `Avatar`, `AvatarStack` | A member (initial on their color, optional today ring), a row of up to five members then "+N" |
| `Sheet` | Bottom sheets for a short task (invite, check in, confirm). Title, close button, one primary action |
| `Banner` | A message that stays true until it changes (wrong password, offline, your turn). Inline; `floating` only for app-wide notices |
| `Toast` (`useToast`) | A short confirmation after an action, above the tab bar |
| `QrCode` | A scannable code for a link |
| `Segmented` | A small set of exclusive options (language, theme) |
| `Skeleton`, `Spinner` | Loading content (skeleton) and loading actions or whole pages (spinner) |
| `TabBar`, `Icon` | Main navigation; the shared icon set (Lucide shapes, stroke 1.75) |

Rules:
- A feature needs something new? Add or extend a component in `shared/ui` (with all its states),
  list it in this table, show it on `/design`, then use it. Never style a one-off button, field or
  pill inside a feature.
- Every component handles its states: default, pressed, focus-visible, disabled, loading and error
  where relevant. Touch targets are at least `--tap-min`.
- Every screen designs its loading, empty and error states.
- Icons: add new ones to `Icon.tsx` (copy the Lucide shape). 24px in the tab bar, 20px in buttons
  and rows, 16px inline with small text. Icon-only buttons need an `aria-label`.

## Motion

| Preset | Feel | Use for |
|---|---|---|
| `snappy` | Fast, firm | Buttons, toggles, small feedback |
| `bouncy` | Playful overshoot | A check mark popping in |
| `gentle` | Soft, slower | Sheets, page and large-surface transitions |

- Import from `@/shared/motion` only (enforced): `motion`, `AnimatePresence`, `useSpring(name)`,
  `variants` (`popIn`, `fadeUp`), `staggerStep`, `pressScale`.
- Short and only in answer to a tap. Animate only `transform` and `opacity`.
- `useSpring()` returns a short fade when the user prefers reduced motion; `MotionConfig` in the
  app providers does the same for every animation.
- CSS transitions use `--duration-*` and `--ease-*` tokens (enforced).

## Layout

Phone first, 390px reference, content column up to `--content-max-width`. The tab bar has Today,
Crew and Me in v1 (the raised check-in button and News come with their features). Use `Screen`
for safe areas and `100dvh`.

## Not in this version

Growing trees and other illustrations, confetti, the Wheel of Doom, reactions, push notifications.

## Guardrails (run by `make check`)

| Rule | Tool |
|---|---|
| No hex, rgb, hsl or named colors outside `tokens.css` | Stylelint `color-no-hex`, `color-named`, `function-disallowed-list` |
| Colors, spacing, fonts, font sizes and weights, line heights, radii, shadows, z-index use `var(--...)` | Stylelint `declaration-strict-value` |
| No raw durations in `transition` or `animation` | Stylelint `declaration-property-value-disallowed-list` |
| No inline `style` props (except `shared/ui` and `/design`) | ESLint `react/forbid-dom-props` |
| No raw `button`, `input`, `textarea`, `select`, `dialog` in features | ESLint `react/forbid-elements` |
| No user-visible text literals in JSX | ESLint `react/jsx-no-literals` |
| Animation only via `@/shared/motion` | ESLint `no-restricted-imports` |
| Dark blocks identical, contrast 4.5:1, `/design` tokens exist | Vitest `src/design/tokens.test.ts` |
| Every `shared/ui` export documented here and shown on `/design` | Vitest `src/design/designSystem.test.ts` |

## Changing the look

1. Edit `tokens.css` (primitives first) and, for feel, `shared/motion/presets.ts`.
2. Restyle components in `shared/ui` if their shape changes.
3. Update this page, check `/design` in light and dark, then the real screens.

Screens should not need changes for a new look. If one does, the rule it broke belongs here.
