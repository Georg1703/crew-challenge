# Plan: missed windows in the journal, notes on check-ins, short punishment texts

Status: stages 0 to 3 committed (2026-10-15); stage 4 (cleaning) built, not committed. Section A
agreed as proposed; section B redesigned with the owner the same day (one note per check-in,
written with it, never edited), defaults B4-B7 accepted; section C defaults accepted. Five stages
on one branch (`feat/missed-notes`), one commit per stage, each committed after the owner's
review.

## Goal

1. **Missed window card.** When a participant's window fails and the wheel opens their spins, the
   crew sees it in the journal right away: "Ana missed the week: 1 of 3 - owes 2 spins". Today
   the journal shows nothing until Ana spins, and a spin never expires.
2. **Notes.** A participant can add a few words (text and emojis) to the day's check-in, while
   checking in: one note a check-in, kept with it and shown on its journal card, never edited.
   Photos and videos stay separate, as today.
3. **Short punishment texts.** Punishments of different lengths make the spins page look uneven.
   Everywhere a punishment shows, it takes one line, cut with "..." where the line ends; a tap
   on a cut one shows the whole text in a small bubble.

Scope: notes extend the daily check-in and the missed card extends the journal and the wheel
(v1 items). Nothing here is on the after-v1 list.

## What changes for members

| | Today | After |
|---|---|---|
| A window fails (challenge with punishments) | Nothing in the journal until the spin | A card within 15 minutes: who, what failed, how many spins they owe |
| Today's challenge card, before the check-in | Hold or "+N", photos | The same, plus an optional "Note" box that goes with the check-in |
| Today's challenge card, after the check-in | - | No note box: the day's note is written |
| Journal check-in card | Who, what, photos | The same, plus the note under the header line |
| Spins page, the list under the dial | Long punishments wrap: rows of different heights | One line each, "..." at the edge, tap for the whole text |
| Drawn punishment, journal spin cards, challenge page | Wrap, or are cut with no way to read them | One line, "..." at the edge, tap for the whole text |

## Decisions

Proposed defaults, to confirm (answer by number, e.g. "B5: add the button").

**A. Missed window card**
- A1. Only on challenges with punishments, where spins exist ("after a spin was created"). A
  failed window on a challenge without punishments gets no card.
- A2. One card per failed window, not one per spin: "owes 3 spins" on one card.
- A3. It is written when the spins open (the job runs every 15 minutes), placed at that time,
  under that crew day: a week that ends Sunday shows on Monday between 00:00 and 00:15.
- A4. No cards for windows that failed before this ships (no backfill).
- A5. The challenge's people see it (participants, viewers, crew admins), like the spin cards;
  it takes reactions and comments like every card.
- A6. The spin's own cards stay: a window reads failed -> drawn -> served.
- A7. The member's own card has no "Spin" button: Today's wheel card already leads there.

**B. Notes** (owner, 2026-10-15: a simple field on the check-in, written only while checking in,
not editable; B1 and B2 are that answer, the rest are defaults to confirm)
- B1. One note per check-in (a participant, a challenge, a day): a field on `CheckIn`. It is
  written with the check-in itself: the hold, or the day's first "+N".
- B2. Never edited. There is no note box once the day is checked in. The only way to change it:
  "Undo" the check-in (the note goes with it), then check in again with a new one.
- B3. Text and emojis only, up to 500 characters (as comments), line breaks kept. Photos and
  videos stay separate (the proof tiles, as today) and are not part of the note.
- B4. Emojis come from the phone's keyboard; no emoji button. (Adding the comments' emoji button
  is small: it moves the emoji sheet out of `Comments.tsx` so both use it. Say if wanted.)
- B5. Optional on every challenge; the proof rules do not change.
- B6. The journal shows it on the check-in's card, under the header line. Later "+N" and
  photo cards that day carry no note. Today's card does not show it after the check-in (the
  journal does).
- B7. The note being typed is not saved: leaving the screen loses it (no browser storage).

**C. Short punishment texts**
- C1. One line everywhere, cut with "..." where the line ends, so rows line up. Not a fixed
  number of characters: a narrow row cuts sooner than a wide one. (The server already caps a
  punishment at 80 characters.)
- C2. A tap on a cut text shows a small bubble with the whole text, over the line (under it when
  there is no room), inside the screen. A tap outside, a second tap, Escape or scrolling closes
  it. A text that fits does nothing on tap.
- C3. Where: the list under the dial, the drawn punishment on the spins page, the journal's spin
  and served cards, the challenge page's punishments. Not changed: the wizard's punishment
  fields (you type it there), screen-reader labels (they read the whole text), the proof
  viewer's caption (already cut; taps there belong to the photo), Django admin.

## Made generic on the way

Only where something is used twice now (AGENTS.md rule 6):
- **`TruncatedText`** (new, `shared/ui`): one line, "...", the bubble on tap. Used in four places
  in stage 3; any long label later.
- **`usePopover`** (new, `shared/ui`, internal): placing a floating panel by the element that
  opened it (above, else below, inside the screen) and closing it (Escape, a tap outside,
  scrolling). Moved out of `ReactionMenu`, which keeps its behaviour; the bubble uses it too.
- **`FeedCard`** gains `note` (the member's words): any card kind can carry words later. `highlight.text` takes a node so a punishment can be a `TruncatedText`.
- Reused, not rebuilt: `journal.post` writes the new card; `describeFailed`
  (`features/doom/describe.ts`) says what failed; the existing check-in endpoint takes the note
  (no new endpoint); `TextArea` is the note box.

## 1. Missed window card

### Data

```
JournalEntry.Kind  + FAILED = "failed"   ("A window failed: spins owed")

a failed card
  subject    the window's first spin (number 1)   - unique (kind, subject, day): written once
  member     who failed;  challenge: the spin's   - who sees it, as for spin cards
  day        the crew day the spins opened; placed when they opened (the card is written then)
  facts      window_first, window_last, need_kind, need, done, spins (how many it owes)
```

Migration: `journal` (choices only, no SQL).

### Writing it

```
doom.open_spins()                     every 15 minutes; now one transaction
  1. insert the spins owed            unchanged (unique key: challenge, member, window, number)
  2. for each window this run opened  its spin number 1, found by the ids this run gave its rows
       write_failed_card(first, spins) journal.post("failed", first, ...), next to write_cards
```

One transaction: if writing a card fails, the run's spins roll back too and the next run opens
both. Running twice writes nothing new (spins: their unique key; cards: `journal.post`).

### API

`GET /api/v1/journal`: `kind` gains `failed`; each card gains `failed: FailedFactsOut | null`
(window_first, window_last, need_kind, need, done, spins). `make schema`.

### Screen

`FailedFeedCard` in `features/doom`, next to `SpinFeedCard`, drawn by `JournalCard` for
`entry.failed`: the member's avatar, "Ana fell short" (`doom.feed.failed`), the challenge chip, the
time, and two facts: what failed (`describeFailed`: "Week 5 - 11 Oct: 1 of 3") and "Owes 2 spins"
(`doom.feed.owes`, plurals ro + en).

### Tests

- A failed week writes one card with `spins` = the spins it opened; a missed day writes one; a
  missed total writes one with `spins` = 1.
- A second run writes nothing; a run the next day writes nothing for that window.
- No card for a met window, a challenge without punishments, a viewer, or spins that existed
  before the run.
- A leaver's cut window gets its card.
- Midnight and the DST night: the card sits under the day the spins opened.
- The card is visible to the challenge's people only; reactions and comments work on it.
- Vitest: `JournalCard` draws a failed card with both facts.

## 2. Notes

### Data

```
CheckIn     + note  CharField(500, blank, default "", db_default "")   the day's note; "" when none
card facts  + note  on the check-in's card (the day's first post); null on later posts
```

Migration: `checkins` (add the column with a database default, so the release before keeps
inserting check-ins). Older cards have no `note` in their facts: the API gives null.

### Rules (`checkins/services.py`)

```
check_in(by, challenge_id, day, amount=None, note="")
  note: stripped; over 500 characters             -> ValidationFailed on `note`
  a note on a post that is not the day's first    -> ValidationFailed on `note`
                                                     ("The note goes with the check-in.")
  the day's first post: CheckIn.note = note; write_card freezes it on that post's card
  everything else (counting, proof, files): as today

undo_last: undoing the day's first post clears the note (the check-in row goes, or stays
           `pending` for its draft files with an empty note)
```

### API

- `POST /api/v1/challenges/{id}/check-ins`: `CheckInIn` gains `note` (optional, up to 500,
  default "").
- `GET /api/v1/journal`: check-in facts gain `note` (string or null).
- `make schema`.

### Screen

```
CheckInCard (Today and the check-in sheet), before the day's check-in
  [ challenge head ]
  [ Note (optional) .................. ]          TextArea, 500; cleared when the check-in
                                                  succeeds, kept when it fails
  [ hold to check in ]  or  [ +1 ][ +5 ][ +10 ][ Other ]    the note goes with these
  [ week strip ]
  [ photos and videos ]                           separate, as today

after the check-in: no note box (the card as today)
```

- `useCheckIn` sends `note` with the day's first post only.
- `JournalCard`: a check-in card with a note shows it under the header line through
  `FeedCard`'s `note` (line breaks kept, long words wrap).
- i18n ro + en: `checkins.note`, `checkins.notePlaceholder`.
- `docs/design-system.md`: the `FeedCard` row mentions the note; `/design` shows a card with one.

### Tests

- A note with the hold, and with the first "+N": stored on the check-in, frozen on that card.
- A note on a later "+N" or on photos added later: refused; the post without a note works.
- Over 500 characters refused; spaces only means no note; emojis (with skin tones and joined
  ones) come back exactly.
- Undo of the check-in clears the note (row gone, or `pending` with draft files); checking in
  again takes a new one.
- A challenge that asks for proof: the check-in with a note still needs a photo or video.
- Vitest: the card sends the note with a hold and with a chip; no note box after the check-in;
  the note stays after an error. The journal card shows the note.
- e2e (`checkins.spec.ts`): check in with a note; the journal card shows it.
- Seeds: a few notes in `seed_demo_history`.

## 3. Short punishment texts

### `TruncatedText` (`shared/ui`)

```
TruncatedText({ text, className? })
  one line; "..." where the line ends (CSS: nowrap, hidden overflow, text-overflow: ellipsis)
  the whole text stays in the page: screen readers read it all; `title` shows it on hover
  tap when cut (scrollWidth > clientWidth) -> bubble with the whole text, placed by usePopover
  bubble: surface, border, shadow, wraps, at most the screen's width less the margins;
          appears with a `shared/motion` preset (none with reduced motion); --z-popover
```

### Where

| Where | File | Change |
|---|---|---|
| Spins page, the list under the dial | `features/doom/components/SpinCard.tsx` (`.text`) | wraps -> `TruncatedText` |
| Spins page, the drawn punishment | `SpinCard.tsx` (`<h2>`) | wraps -> `TruncatedText` |
| Journal, spin drawn and served | `SpinFeedCard.tsx` -> `FeedCard` `highlight` | wraps -> `TruncatedText` |
| Challenge page, Punishments | `features/challenges/routes/ChallengeRoute.tsx` (`ListRow` title) | already cut by `ListRow` -> `TruncatedText` adds the bubble |

`docs/design-system.md` gains the `TruncatedText` row; `/design` shows a short and a long one
(both enforced by `designSystem.test.ts`).

### Tests

- Vitest: a cut text opens the bubble on tap and closes on a second tap, a tap outside, Escape;
  a text that fits opens nothing (jsdom has no layout: the test sets `scrollWidth` and
  `clientWidth`).
- The `ReactionMenu` tests pass unchanged after `usePopover` moves out.
- A hold on a journal card still opens the reactions; a tap on its punishment opens the bubble.

## Stages

| Stage | What works at the end | Size |
|---|---|---|
| 0. Plan | This plan; updates to it ride with the stage they change | S |
| 1. Missed window card | Section 1: kind, writer in `open_spins` (one transaction), API, `FailedFeedCard`, tests, `make schema`; glossary **Card**, AGENTS.md game rules, `docs/plans/journal.md` card table and `docs/architecture/api-conventions.md` kinds list gain `failed`; the demo crew shows one after `make seed` | S |
| 2. Notes | Section 2: column, rules, API, the note box, the note on cards, tests, e2e, seed; glossary **Note**, AGENTS.md game rules (a check-in may carry a note) | S |
| 3. Short punishment texts | Section 3: `TruncatedText`, `usePopover` out of `ReactionMenu`, the four places, design docs and `/design`, tests | S |
| 4. Cleaning | See below | S |

Each stage: `make check` passes; stages 1 and 2 also `make e2e`. Each is safe to ship on its
own: an older app shows nothing for a `failed` card it does not know, and checks in without a
`note`.

## Stage 4: cleaning

The three features read again as a whole, with the code around them, to leave it simpler and
correct.

**Where:** every file stages 1 to 3 touched, plus what they lean on: `apps/doom` (services,
selectors, tasks, tests), `apps/checkins/services.py` and `card_facts`, `apps/journal` (services,
selectors, API), `features/doom`, `CheckInCard`, `JournalCard`, `FeedCard`, `ReactionMenu`,
`ListRow`, the i18n files for the keys these use.

**Look for:**
- Dead code: functions, props, CSS classes, i18n keys and test helpers nothing uses; branches no
  caller reaches.
- Duplicates the new pieces should own: hand-written ellipsis CSS that `TruncatedText` covers,
  placement or dismissal code that `usePopover` covers, failure wording that `describeFailed`
  covers.
- Helpers used once that read better inline; names that no longer say what a thing does.
- Mistakes: comments and docstrings that no longer match the code, `help_text` and API
  descriptions that are out of date, missing cases in tests (midnight, DST, leavers, empty note),
  tests that cover the same thing twice.

**Rules:**
- Deletions, merges, renames and fixes only. No new behaviour; API shapes stay as stage 3 left
  them.
- A real bug found is fixed with a test that fails before the fix.
- Anything bigger (a behaviour change, a new rule) is listed in the stage summary for the owner,
  not done.
- The summary lists what was removed or changed and why, file by file.
- `make check` and `make e2e` stay green.

## Docs touched

| Doc | Stage |
|---|---|
| `docs/plans/missed-notes.md` (this) | 0 |
| `docs/glossary.md` (Card), `AGENTS.md` game rules, `docs/plans/journal.md` (card kinds), `docs/architecture/api-conventions.md` (kinds) | 1 |
| `docs/glossary.md` (Note), `AGENTS.md` game rules, `docs/design-system.md` (`FeedCard` note), `docs/architecture/api-conventions.md` (check-in body) | 2 |
| `docs/design-system.md` (`TruncatedText`) | 3 |
| Any doc that stage 4 finds out of date | 4 |

## Risks

| Risk | Answer |
|---|---|
| An older app (cached PWA) meets a `failed` card | `JournalCard` draws nothing for a kind it does not know; it shows after the update |
| A run fails halfway | One transaction: spins and cards roll back together; the next run, 15 minutes later, writes both |
| A card twice | The spin's unique key and `journal.post`'s (kind, subject, day) |
| Lengths differ: the browser counts an emoji as 2 of 500, the server as 1 | The browser stops first, never the server |
| A tap on a punishment inside a card that opens reactions on hold | A tap opens the bubble, a hold the reactions; opening one closes the other (a tap outside) |
| jsdom has no layout | Tests set `scrollWidth` and `clientWidth` on the element |

## Out of scope

- Editing a note, or a note box after the check-in (only "Undo" of the check-in, then a new one).
- Notes on later "+N" posts, on photos added later, when serving a punishment, on past days.
- Showing the note on Today, the board or the day sheet (the journal card shows it).
- Missed cards for challenges without punishments.
- Notifications ("Ana missed the week"): after v1, with Web Push.
- Formatting, mentions or link previews in notes.
- Who watched a proof video (discussed separately; a plan of its own if wanted).
