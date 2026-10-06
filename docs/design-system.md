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
| success | `--color-success`, `--color-success-soft`, `--color-success-line` | Done, checked in, the active tab; `-line` borders a card on `-soft` (a streak milestone) |
| warning | `--color-warning`, `--color-warning-soft` | Attention: offline, paused, large file |
| danger | `--color-danger`, `--color-danger-soft` | Errors, missed days, destructive actions |
| focus | `--color-focus-ring` | Keyboard focus outline (2px) |
| overlay | `--color-overlay` | Dim layer behind sheets |
| avatar-1..5 | `--color-avatar-1` .. `-5`, `--color-on-avatar` | Member colors, white initials |
| code | `--color-code-bg`, `--color-code-fg` | QR codes: dark on white in both themes |
| media | `--color-media-bg`, `--color-on-media`, `--color-media-scrim` | Behind photos and videos (proof tiles, the viewer): the same near-black in both themes; marks over them are white on the scrim |
| media pending | `--media-pending` | Stripes in the surface colors on a video being converted (`ProofTile`, `ProofMosaic`) |

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
  small cells and thumbnails, `--radius-media-inner` 4px between the proofs of a `ProofMosaic` (its
  outer corners keep the card's), `--radius-xs` 2px only for the bars of `DayBars` and `MiniWeek`,
  `--radius-full` for avatars and pills. No other values (enforced).
- Space: 4px grid, `--space-1` .. `--space-12`. Screen gutter `--space-5`, sections `--space-6`
  apart, card padding `--space-4` (enforced for margin, padding and gap). `--space-hair` (2px) only
  between the bars of `DayBars`.
- Depth: `--shadow-card` on cards and lists, `--shadow-sheet` on sheets, toasts and floating
  banners. Nothing else casts a shadow. Dark cards rely on their border.
- Sizes: `--tap-min` 44px (every control), `--button-height` 52px, `--button-height-sm` 44px,
  `--input-height` 48px, `--avatar-sm/md/lg` 28/40/64px, `--tabbar-height` 64px,
  `--progress-ring-size` 168px (the day ring), `--day-bar-height` 20px (a bar in `DayBars`),
  `--proof-tile-size` 72px (the most a proof thumbnail grows; grids shrink it on narrow screens),
  `--story-avatar-size` 68px and `--story-avatar-size-lg` 88px (`StoryAvatar`),
  `--mini-bar-height` 18px and `--mini-bar-width` 8px (a day in a `MiniWeek`).
  `--ring-current` marks today in a week strip.
- Layers: `--z-sticky` (a `DayDivider` over the cards under it), `--z-tabbar`, `--z-sheet`, `--z-viewer` (above a sheet it opens from), `--z-toast`.

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
| `Sheet` | Bottom sheets for a short task (invite, check in, confirm, a day of the board). Title, close button, one primary action. Escape closes it unless a layer above (the proof viewer) took it |
| `Banner` | A message that stays true until it changes (wrong password, offline, your turn). Inline; `floating` only for app-wide notices |
| `Toast` (`useToast`) | A short confirmation after an action, above the tab bar; optionally one action ("Undo") for 5 seconds |
| `QrCode` | A scannable code for a link |
| `Segmented` | A small set of exclusive options (language, theme) |
| `OptionList` | One choice among a few that each need a line of explanation (how often, what proof) |
| `ChipGroup` | Several short choices that combine (days of the week, quick ideas) |
| `CheckList` | Pick several rows, each with an optional avatar and a line of detail (who takes part); a row can be locked |
| `Stepper` | A small whole number with minus and plus (times a week) |
| `TextArea` | A labelled multi-line field (rules, notes); same states as `TextField` |
| `Toggle` | An on/off setting with a label and an optional explanation |
| `StepProgress` | Where you are in a multi-step form (segments) |
| `IconPicker` | Pick one icon from a small set (a challenge's icon) |
| `HoldButton` | Press and hold (0.6 s) to confirm a check-in; letting go cancels; keyboard confirms at once |
| `ProgressRing` | Today's ring: one segment per thing to do, full / half / empty; closes with the center popping to "done" |
| `ProgressBar` | Progress toward a goal (pages, km, times this week); full turns success |
| `DayMark`, `WeekStrip` | A day as a shape (done check, half ring, ring, cross, dot, faint ring); seven of them, Monday to Sunday, with a small dot under the days with proof |
| `DayBars`, `DayBar`, `DayBarsAxis` | A person's month as one row of thin bars (done tall and green, missed short and red, due outlined, coming up faint) and, with `proofs`, a dot under the days with proof; a single bar for a legend; the day numbers above the rows. With `onPick` the day numbers become buttons (named by `labels`) and a tap on a row picks the day under the finger |
| `ProofTile` | A proof as a square thumbnail that fills its grid cell, its state readable by shape: a play mark on a ready video, a filling ring while uploading, pause while waiting, a clock while a video is prepared, an alert when it failed. A ready video shows its length in a pill; a video being prepared with no poster shows calm stripes. A button when it opens something; an optional remove button (today only); `fill` fills a mosaic cell instead of staying square |
| `ProofMosaic` | A check-in's proofs laid out by count: one in a 4:3 box, two side by side, three or more as one big and two small with "+N" over the third. Tapping a tile opens the viewer at that proof |
| `ProofViewer` | Proofs full screen: swipe, arrows or arrow keys between them; pinch or double tap zooms a photo; a video plays inline, muted until tapped (HLS, with hls.js loaded only where needed) |
| `FeedCard` | One moment in the crew's journal, as a card of its own: who (an avatar with today's ring, or a stack for a group), what, the challenge as a chip and when; then by kind a `ProofMosaic`, an amount with a bar to the target, or a milestone's big number; a footer with `MiniWeek` and short facts. `tone="success"` for a milestone or the whole crew finishing the day |
| `StoryAvatar` | A member with today's ring split into one segment per challenge due today (done green, started faint green, to do grey; nothing due: a plain grey ring), their name and "2/2" under it, and a count of new proofs. A link to the member's page; `lg` at the top of that page |
| `MiniWeek` | The last seven days as small bars with the shapes of `DayBars`, today outlined; read as one summary |
| `DayDivider` | A day in the crew's journal: its name, a line and what happened; sticks to the top while that day scrolls |
| `StatGroup` | Up to three numbers in one card, divided, each with a short label under it; a number can be success green |
| `ChallengeChip` | A challenge named inside a card: its icon in a small accent circle and its title, cut with an ellipsis |
| `ProofAddTile` | The "+" tile beside proof tiles: opens the phone's picker (camera or library) for the kinds a challenge takes |
| `Skeleton`, `Spinner` | Loading content (skeleton) and loading actions or whole pages (spinner) |
| `TabBar`, `Icon` | Main navigation, with an optional raised action (check in), its count and, while proofs upload, a thin progress ring; the shared icon set (Lucide shapes, stroke 1.75) |

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
Crew, the raised check-in button and Me in v1 (News, after it, will put the button in the center). Use `Screen`
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
