# Plan: reactions (simple version, generic targets)

Status: draft for review. Branch: `feat/reactions` from `main`.
Design reference: the canvas "Reactii - 3 variante" (variant D for the chips under the card,
E-cine for the "who reacted" sheet). Order of priorities: user experience, architecture,
efficiency.

## Goal

A crew member can answer a check-in with one emoji in two taps, and everyone sees who cheered
whom. Reactions are built as a building block: the same model, API and UI can later go on a
challenge, a proof or anything else in the crew, by registering it, without a new table or
endpoint. Simple first: no custom reaction texts, no notifications, no live updates.

## Decisions (agreed)

| Topic | Decision |
|---|---|
| Picking | A "react" button opens a quick row of 6 emojis plus "+", which opens the Emoji Mart picker (any emoji, with search). |
| Per person | One reaction per target. Picking another replaces it; tapping your own chip removes it. |
| Target (now) | Single check-in cards (with a proof, a number or a milestone). Grouped "checked in" cards and the crew-done card get none for now. |
| Target (model) | Generic: a reaction points at any registered object (generic foreign key). Challenges, proofs and others come later by registration only. |
| Who reacted | Each chip: the emoji and up to 3 small avatars (then "+N"). Press and hold a chip, or "Who reacted" in the quick row, opens a sheet listing everyone. |

## Decisions with a proposed default (confirm or change)

1. **Scope change.** Simple reactions move into v1. AGENTS.md, `docs/design-system.md`
   ("after v1" list) and `docs/glossary.md` change with the feature; reaction push
   notifications and per-person custom reactions stay after v1.
2. **Quick row:** thumbs up, fire, clapping hands, flexed biceps, face with tears of joy, red
   heart. The same 6 for everyone; making them configurable per person (with a short text, the
   earlier idea) is the next version.
3. **Your own check-in:** you can react to it too (Telegram does; harmless in a family).
4. **Freshness:** others' reactions appear when the feed refreshes (every 60 s, on focus, on
   pull). No websockets.
5. **Ordering of chips:** by the time the emoji was first used on that target, so chips do not
   jump around when counts change.
6. **New rule in AGENTS.md** ("How to work in this repo"), as asked:
   "When planning, look for what can be generic (a model, an endpoint, a component, a hook) so
   the next feature reuses it, and for what can be simpler. Do it where it pays off now or
   clearly soon, say why in the plan, and do not build for imagined needs."

## Generalising and simplifying (applying the new rule)

| What | Generic version | Why now |
|---|---|---|
| Reaction model | `apps.reactions`, generic foreign key to any registered target | Asked; challenges and proofs are the obvious next targets |
| API | One endpoint for every target type: `/api/v1/reactions/{target}/{id}` | No new URLs or views per target |
| Feed payload | One `ReactionSummary` serializer, embedded wherever a target is shown | Same shape for every target, one client type |
| Frontend | A `reactions` feature: `<Reactions target id summary />` with chips, quick row, picker and sheet | Any screen gets reactions with one component |
| Cache update | The hook takes the owner's update function; the reactions feature knows no other feature's cache | Keeps features independent (ESLint boundaries) |
| Long press | `usePress` in `shared/lib` (tap, long press, keyboard) | Proof tiles and avatars will want long press too |
| Emoji picker | `EmojiPicker` in `shared/ui`, not tied to reactions | Usable later for challenge icons or messages |

Not generalised: the "who reacted" sheet stays inside the reactions feature. The closest
existing sheet (`ParticipantsSheet`) is an editor with a picker, not a list, so a shared
"people sheet" would be a guess today; extract it when a second list of people appears.

## Library: Emoji Mart

- `emoji-mart` 5.6.0 (picker, a web component) and `@emoji-mart/data` 1.2.1 (Unicode 15,
  native set). Dependency reason for the PR: "full emoji picker with search and skin tones,
  loaded only when opened".
- **Not** `@emoji-mart/react`: its peer range stops at React 18 (last release Jan 2023). The
  core works with React 19; our own wrapper is ~20 lines.
- Last release April 2024: stable but quiet. If it ever breaks, `EmojiPicker` is the only place
  to change (alternative: `frimousse`, React 19 native, headless).
- Size: picker ~30 KB gzip, native data ~83 KB gzip. Both are `import()`ed when the picker first
  opens; the journal's first load does not change. The service worker does not precache them.
- No Romanian in Emoji Mart: its texts (search placeholder, category names, "no results") come
  from our `ro.json` / `en.json` and are passed as its `i18n` object.
- It draws inside a shadow root, so tokens cannot reach it by CSS. The wrapper reads the
  semantic tokens with `getComputedStyle` and sets Emoji Mart's variables (`--rgb-accent`,
  `--rgb-background`, `--rgb-color`, `--font-family`, `--border-radius`); light and dark follow
  the app theme. No hex values in our code.
- Settings: `set: "native"`, `previewPosition: "none"`, `skinTonePosition: "search"`,
  `navPosition: "top"`, `maxFrequentRows: 1`, `emojiButtonSize: 44` (tap target),
  `dynamicWidth: true` (fills the sheet). Its "frequently used" list stays in its own
  localStorage (a cache; losing it is harmless).

## Backend: new app `apps.reactions`

Layering: reactions build on crews (members, crew scope) and know nothing about challenges or
check-ins. Domain apps register their targets with it. New import-linter contract: "Reactions
know their targets only through the registry" (`apps.reactions` may not import
`apps.challenges`, `apps.checkins`, `apps.media`).

**Model** `Reaction(CrewScopedModel)`:
- `target_type` (FK `ContentType`, protect), `target_id` (UUID), `target`
  (`GenericForeignKey`); every domain id is a UUID, so one column fits all.
- `member` (FK, cascade), `emoji` (CharField 32), timestamps from the base.
- Unique `(target_type, target_id, member)`; index `(target_type, target_id, created_at)`.
- `crew` is copied from the target (every target is crew-scoped), so crew filters keep working.
- Not soft-deleted: removing a reaction removes the row. Migration `reactions/0001_initial`.

**Integrity without a database foreign key.** A generic key has no FK constraint, so:
- each target model declares `reactions = GenericRelation("reactions.Reaction",
  content_type_field="target_type", object_id_field="target_id")`, which deletes its reactions
  when the target is deleted (CheckIn now);
- a test walks the registry and fails if a registered model lacks that relation;
- soft-deleted targets (challenges later) are hidden by their own `find`, so their reactions
  are never shown or changed.

**Registry** (`apps/reactions/targets.py`):
```python
@dataclass(frozen=True)
class Target:
    key: str                                         # public name in the API: "check_in"
    model: type[CrewScopedModel]
    find: Callable[[Member, UUID], Model | None]     # visible and reactable, else None
```
`register(target)` from the owner's `AppConfig.ready()`. Check-ins register `check_in` with
`find = selectors.reactable_check_in` (a challenge the member can see, and a single card: a
shown proof, a number, or a milestone day; the same rule as the journal).

**Services**
- `react(*, member, target, target_id, emoji) -> Summary`: `find` the target (else
  `target_not_found`), validate the emoji, upsert on the unique key (a double tap is safe).
- `unreact(*, member, target, target_id) -> Summary`: delete the member's row; none is fine.
- Emoji check without a new dependency: 1-32 characters, at least one of Unicode category
  `So`, and only `So`, `Sk`, `Mn`, `Me`, `Cf`, `Nd` (keycaps): rejects text, spaces and markup.
  Error `invalid_emoji`.

**Selectors:** `summaries(*, member, target, ids) -> dict[UUID, Summary]` in one query for a
whole page; `Summary` = `groups: [{emoji, member_ids}]` (first-use order) + `mine`.

**API**
- `PUT /api/v1/reactions/{target}/{id}` body `{"emoji": "..."}` -> 200 `ReactionSummary`.
- `DELETE /api/v1/reactions/{target}/{id}` -> 200 `ReactionSummary`.
- `{target}` is an enum built from the registry (`check_in` for now), so the OpenAPI contract and
  the TypeScript client list exactly the registered types.
- `ReactionSummary` = `{groups: [{emoji, member_ids}], mine: string | null}`. Member names and
  avatars come from the crew members the screen already has.
- The feed item gains `reactions: ReactionSummary` (the checkins API reuses the reactions
  serializer and calls `summaries` once per page).
- Errors: `target_not_found` (404, also when not visible or not reactable), `invalid_emoji`
  (400, `fields.emoji`), unknown `{target}` -> 404.
- `make schema` after the serializers.

**Tests:** react, replace, unreact twice; not visible / plain check-in / unknown target -> 404;
bad emoji (text, spaces, 33 characters, `<b>`); ZWJ family and skin tones accepted; deleting a
check-in deletes its reactions; registry relation check; feed shows groups in first-use order
with `mine` and adds one query per page; reactions cannot read another crew's targets.

## Frontend

**`shared/lib`**
- `usePress({ onPress, onLongPress, delay = 500 })`: pointer and keyboard (Enter, Space,
  ContextMenu key), cancels on move, haptic tick on long press (`haptics.ts`).

**`shared/ui` (each with all states on `/design`, documented in `docs/design-system.md`)**
- `EmojiPicker`: the Emoji Mart wrapper (inside a `Sheet` by the caller); lazy, `Skeleton` while
  loading, error `Banner` with "Try again".
- `ReactionChips`: chips under a card. A chip: the emoji, up to 3 `Avatar` (xs) overlapping,
  then "+N". Yours uses the accent surface and `aria-pressed`. Labels: "Fire, from you and Ana".
- `ReactionMenu`: the quick row, a popover above the react button (6 emoji buttons of 44 px,
  "+", and "Who reacted" when there are reactions). `snappy` spring, closes on outside tap and
  Escape, focus moves in and back.
- New icon `smilePlus` (Lucide) in `Icon`.

**New feature `reactions`** (`src/features/reactions/`, public API in `index.ts`)
- `<Reactions target="check_in" id={...} summary={...} people={members} onChange={patch} />`:
  chips + react button + quick row + picker sheet + "who reacted" sheet. Tap toggles yours, long
  press opens the sheet.
- `useReact(target, id, { onChange })`: `PUT`/`DELETE`, optimistic: calls the owner's
  `onChange(summary)` at once, again with the server's summary, or with the old one and a toast
  on error. No knowledge of other features' query keys.
- i18n keys `reactions.*` (react, more, who, count, from, picker texts) in both files; errors
  `target_not_found`, `invalid_emoji`.
- Motion: a new chip scales in with `bouncy` from 0.6 (transform and opacity only); counts change
  without layout jumps; `prefers-reduced-motion` turns the scale off. No sounds.

**Feature `checkins`**
- `FeedCard` gets a `reactions` slot (under the content, above the footer).
- `CrewFeed` renders `<Reactions target="check_in" ...>` on single cards and patches the feed's
  infinite-query cache in its `onChange`. Group cards and the crew card get none.

**Tests:** `usePress` (tap, long press, move cancels, keyboard); chips render groups and "+N";
toggle with optimistic update and rollback; quick row picks and closes; "+" lazy-loads the
picker (mocked) with Romanian texts; Escape and focus return. Playwright: Ana reacts to
Bogdan's proof card, changes it, Bogdan sees it after a refresh, Ana removes it.

## Commits (one PR)

1. `feat(backend): add generic reactions` (app, registry, model, migration, services,
   selectors, API, import-linter contract, tests).
2. `feat(backend): let crews react to check-ins` (CheckIn registration and `GenericRelation`,
   feed `reactions`, tests, schema).
3. `feat(frontend): add usePress, emoji picker and reaction chips` (shared/lib, shared/ui,
   `/design`, design-system docs, dependencies).
4. `feat(frontend): react to check-ins in the journal` (reactions feature, CrewFeed wiring,
   i18n, tests, e2e).
5. `docs: move simple reactions into v1 and add the generalise rule` (AGENTS.md, glossary,
   `docs/architecture/backend.md` app list and layers, design system "after v1" list).

## Acceptance

- Two taps from the journal to react; the chip appears within 100 ms (optimistic).
- One reaction per person per target; change and remove work; double taps are safe.
- Who reacted is reachable by long press and by the quick row's "Who reacted".
- Adding a new target type needs only: a `GenericRelation` on its model, a `register(...)` call
  with its `find`, and `<Reactions target=...>` where it is shown.
- The journal's first load does not grow by more than 3 KB gzip; the picker loads on demand.
- `make check` and `make e2e` pass; tested on an iPhone and an Android phone (`make preview`).

## Later (not in this plan)

Per-person quick row with short texts (up to 10 characters), reactions on challenges, proofs
(in the viewer) and grouped cards, double tap on a photo to react, push notification "Ana
reacted to your proof", live updates.
