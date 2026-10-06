# Plan: the Echipa tab, version 2 (the crew's journal)

Status: draft for review. Branch: `feat/team-tab-v2` from `feat/proofs`.
Design: the canvas "Echipa - 3 variante", second row: `Echipa.dc.html` (the screen),
`Componente.dc.html` (new components and tokens), `Membru-v2.dc.html` (the member page).
Order of priorities: efficiency, user experience, then architecture.

## Goal

Echipa answers two questions at a glance: how is everyone doing today, and what did the crew
just do. Tapping a person shows their month and their proofs. The proof stays the picture.

## Decisions (agreed)

| Topic | Decision |
|---|---|
| Direction | Variant C: a row of story avatars, then a journal of separate cards, grouped by day. |
| Member page | Kept, in its improved form (stats, a month per challenge with proof dots, proofs by day). |
| Components | New `shared/ui` pieces and tokens are allowed when they feel like the existing ones. |

## Decisions with a proposed default (confirm or change)

1. **Streak milestones** at 3, 7, 14 and 30 days in a row, only for challenges with fixed days
   (daily, weekdays). Derived when the feed is read, never stored.
2. **"Whole crew finished the day"** card when every participant finished every challenge due that
   day. Shown under that day's divider, for today only once the last one checks in.
3. **New-proofs badge** is remembered on the device (per crew, per member: the time you last saw
   their proofs). It resets when you open their page or one of their proofs. No new table; a
   synced version can come later.
4. **Members and invites move** to their own screen (`/crew/members`), opened from an icon button
   next to the title. Echipa keeps only the journal.
5. **Proposals** become one slim row under the avatars, only when the pool is not empty:
   "1 propunere asteapta votul tau" (unvoted ones) or "3 propuneri in lista". The big card leaves
   this tab.
6. **Video length**: the phone reads it from the file before upload (`<video>` metadata) and sends
   it with the start request; `Proof.duration` (seconds, nullable) stores it.

## Tokens (`tokens.css`, both themes, `src/design/tokens.ts`, `docs/design-system.md`)

| Token | Light | Dark | Use |
|---|---|---|---|
| `--color-media-scrim` | ink-900 at 80% | black at 70% | Under "+N", a video's length and upload progress on a proof |
| `--color-success-line` | green-100 (`#cfe5d6`) | green-900 | Border of milestone cards on `success-soft` |
| `--media-pending` | two-tone stripes from `surface-sunken` | same, dark | A video being converted |
| `--radius-media-inner` | 4px | 4px | Between proofs in a mosaic; outer corners stay `--radius-sm`+ |
| `--story-avatar-size` | 68px | - | The avatar row and the member page header (88px variant) |
| `--mini-bar-height` | 18px | - | Bars in `MiniWeek` |

The stylelint allow list and the contrast test cover the new colors (white text on the scrim
must reach 4.5:1).

## New and changed `shared/ui` components (each on `/design`, in the docs, with all states)

| Component | What it is | States |
|---|---|---|
| `StoryAvatar` | Avatar inside a ring split into one segment per challenge due today; name and "2/2" under it; optional new-proofs count | done, started, to do, nothing due, new proofs, you, focus |
| `ProofMosaic` | 1 to 5+ proofs laid out by count (1: 4:3; 2: two tall; 3+: one big, two small, "+N" on the third) | each tile's state, keyboard order, tap opens the viewer at that proof |
| `ProofTile` (changed) | Adds the video length pill and the striped "converting" look | photo, video, converting, uploading %, failed + retry |
| `MiniWeek` | The last 7 days as small bars, today outlined (same shapes as `DayBars`) | done, missed, to do, not due, outside |
| `DayDivider` | "Azi" + line + "5 bifari, 9 dovezi"; sticks to the top while that day scrolls | - |
| `FeedCard` | Replaces `FeedItem`. Header (avatar with day ring, challenge chip, time), body by kind, footer (`MiniWeek`, streak, day N of M, proof count) | kinds: proofs, quantity (+N and a bar to the target), plain group ("Ana si Dan au bifat ..."), streak milestone, crew day |
| `StatGroup` | Up to 3 numbers in one card with dividers (number style, small label) | - |
| `ChallengeChip` | Small pill with the challenge's icon and name (used in cards) | - |

`FeedItem` is removed once `FeedCard` replaces it (one commit, docs and `/design` updated).

## Backend

| Change | Where | Notes |
|---|---|---|
| `Proof.duration` | `checkins.models`, migration, start serializer | Seconds, nullable; videos only; validated 0 < d <= 3 h |
| Today: one state per challenge per person | `selectors.today`, `CrewDayOut.challenges: [{challenge_id, state}]` | Feeds the split rings; same query, no extra cost |
| Feed item fields | `FeedItemOut`: `streak`, `day_index`, `day_count`, `week` (7 states), `last_amount`, `target`, `milestone` (`{kind: "streak", n}` or null) | Computed with `days.py` from the records already loaded for the page; one extra query per page at most |
| Day summaries | `GET /feed` response: `days: [{day, check_ins, proofs, crew_done}]` for the days on the page | Counts by `GROUP BY day`; `crew_done` drives the crew-day card |
| Member page | `GET /api/v1/members/{id}/progress?month=YYYY-MM` | Stats (current streak, longest streak, % of due days done this month), per visible challenge: month states + proof days + today's state, proofs grouped by day (30 per page). 404 for another crew. |
| `days.longest_streak` | `checkins/days.py` | Pure, with tests (DST, partial weeks, left early) |

Visibility stays the rule everywhere: only challenges the viewer can see, only proofs the crew
can see. Every new field comes from data that already exists; nothing new is stored except
`Proof.duration`.

## Frontend

| Change | Where |
|---|---|
| Echipa: title + members icon button, `StoryAvatar` row (horizontal scroll, you first, then by progress), proposals row, journal (`DayDivider` + `FeedCard`s, infinite scroll by cursor, plain check-ins grouped on the phone) | `features/crew/routes/CrewRoute.tsx`, `features/checkins/components/CrewFeed.tsx` |
| Members screen: the member list (roles, today), invite button and pending invites for admins | new `features/crew/routes/MembersRoute.tsx`, route `/crew/members` |
| Member page: `StoryAvatar` (88px), `StatGroup`, one card per challenge (`DayBars` + proof dots + streak), proofs by day (`ProofMosaic`), the viewer | new `features/crew/routes/MemberRoute.tsx`, route `/crew/members/:id` |
| New-proofs badge | `features/crew/seen.ts` (localStorage, try/catch, per crew) |
| i18n | `crew.journal.*`, `crew.member.*`, `crew.members.*` in ro and en |

## Performance budget

- Echipa's first view: `GET /today` + `GET /feed` (first page, 20 cards) in parallel; thumbnails
  only (lazy, `loading="lazy"`, fixed aspect boxes so nothing jumps).
- The rings and the mini weeks are CSS and SVG, no images. Motion only for the ring filling and a
  card appearing (presets, reduced motion respected).
- The feed refreshes on focus and every 60 s while visible; new cards slide in at the top.

## Edge cases

| Case | Behaviour |
|---|---|
| A member has nothing due today | Grey ring without segments, "-" under the name |
| More than 8 members | The avatar row scrolls sideways; you stay first |
| A member left a challenge | Their past cards stay; their ring counts only what they still do |
| A challenge you cannot see | Not in rings, cards or the member page |
| Quantity with no target | "+12 pagini, 20 azi" without a bar |
| A video still converting | Striped tile with "Se pregateste"; the length shows once known |
| Milestone and proofs on the same check-in | One proofs card with a milestone line in the footer ("7 zile la rand") |
| Empty crew day | Divider with "nimic inca"; no empty card |
| localStorage blocked | No badge; nothing else changes |

## Commits

1. `feat(frontend): add media and milestone tokens to the design system`
2. `feat(frontend): add story avatar, proof mosaic, mini week, day divider, stat group and chip`
3. `feat(frontend): replace the feed item with the feed card`
4. `feat(backend): give feed items streaks, weeks, amounts and milestones`
5. `feat(backend): add day summaries and per-challenge states for the crew`
6. `feat(backend): add the member progress view and the video length`
7. `feat(frontend): rebuild echipa as the crew's journal`
8. `feat(frontend): add the members screen and the member page`
9. `test(frontend): cover the journal and the member page end to end`

## Tests that must exist

- `days.longest_streak`; milestones at exactly 3/7/14/30 and not again the day after; crew day
  only when everyone due is done.
- Feed: fields per kind, paging with day summaries, visibility; member progress: stats, 404 for
  another crew, hidden challenges absent.
- Components: every state on `/design`; `FeedCard` kinds; `ProofMosaic` 1..6 proofs; `StoryAvatar`
  segments; badge resets.
- E2E: open Echipa, see your ring fill after a check-in, open a member, open a proof.

## Out of scope

Reactions and comments, push notifications, a synced "seen" state, sharing a card outside the app.
