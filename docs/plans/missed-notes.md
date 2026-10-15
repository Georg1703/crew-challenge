# Plan: missed windows in the journal, notes on posts, short punishment texts

Status: section A agreed (the owner asked to build the missed card, 2026-10-15) and stage 1
built, not committed; B and C await the owner. Five stages on one branch (`feat/missed-notes`),
one commit per stage, each committed after the owner's review.

## Goal

1. **Missed window card.** When a participant's window fails and the wheel opens their spins, the
   crew sees it in the journal right away: "Ana missed the week: 1 of 3 - owes 2 spins". Today
   the journal shows nothing until Ana spins, and a spin never expires.
2. **Notes.** A participant can write a few words with a post (text and emojis): with the
   check-in, with a "+N", with photos, or on their own later that day. Every note is a new post
   and a new journal card; a note is never edited.
3. **Short punishment texts.** Punishments of different lengths make the spins page look uneven.
   Everywhere a punishment shows, it takes one line, cut with "..." where the line ends; a tap
   on a cut one shows the whole text in a small bubble.

Scope: notes extend the daily check-in and the missed card extends the journal and the wheel
(v1 items). Nothing here is on the after-v1 list.

## What changes for members

| | Today | After |
|---|---|---|
| A window fails (challenge with punishments) | Nothing in the journal until the spin | A card within 15 minutes: who, what failed, how many spins they owe |
| Today's challenge card | Hold or "+N", photos | The same, plus a "Note" box; the note goes with the next post |
| After the day's check-in | "Post 2 files" when photos are ready | "Post note" when there is only a note; "Post 2 files" when there are files (the note goes with them) |
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

**B. Notes**
- B1. A note belongs to a post: the check-in, a "+N", photos added later, or nothing else (a
  post that is only a note). Each is its own journal card.
- B2. Never edited. Writing more posts a new note and a new card; the earlier ones stay as they
  were. "Undo" removes the latest post, note included (refused once someone else commented, as
  today).
- B3. A note alone cannot be the day's first post: on a challenge without a number the first
  post *is* the check-in, so the note waits for the hold (or a "+N"); "Post note" appears once
  the day is checked in.
- B4. Today only, on days the challenge asks for, participants only: the rules of posting. "Any
  time" means any time until midnight.
- B5. Up to 500 characters (as comments), plain text, line breaks kept. Emojis come from the
  phone's keyboard; no emoji button. (Adding the comments' emoji button is small: it moves the
  emoji sheet out of `Comments.tsx` so both use it. Say if wanted.)
- B6. A note never needs proof: on a challenge that asks for proof, the check-in still needs a
  photo or video; a note posted alone later does not.
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
- **`FeedCard`** gains `note` (the member's words): any card can carry words later (serving a
  punishment, say). `highlight.text` takes a node so a punishment can be a `TruncatedText`.
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
`entry.failed`: the member's avatar, "Ana missed it" (`doom.feed.failed`), the challenge chip, the
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
CheckInEntry  + note  CharField(500, blank)   the post's words; "" when none
card facts    + note  (null when none)
              action  check | amount | files | note   ("note": neither counts nor carries files)
```

Migration: `checkins` (add the column, default ""). Older cards have no `note` in their facts:
the API gives null.

### Rules (`checkins/services.py`)

```
check_in(by, challenge_id, day, amount=None, note="")
  note: stripped; over 500 characters -> ValidationFailed on `note`
  counts:      as today (a "+N" with a number; the day's first post elsewhere)
  proof:       as today, for a post that counts only
  posts when:  it counts, or carries uploaded draft files, or has a note   (else nothing, as today)
  CheckInEntry(note=note); write_card freezes it on the card
```

Undo, the crew's day and the journal's day counts are unchanged: a note post is a post.

### API

`POST /api/v1/challenges/{id}/check-ins`: `CheckInIn` gains `note` (optional, up to 500,
default ""). Journal check-in facts gain `note` and the action `note`. `make schema`.

### Screen

```
CheckInCard (Today and the check-in sheet)
  [ challenge head ]
  [ hold to check in ]  or  [ +1 ][ +5 ][ +10 ][ Other ]    the note goes with these
  [ week strip ]
  [ photos and videos ]
  [ Note (optional) .................. ]                    TextArea, 500; cleared when a post
                                                            succeeds, kept when it fails
  [ Post note ]  or  [ Post 2 files ]                       after the day's check-in, when there
                                                            is a note or ready files; waits
                                                            while files upload (as today)
```

- `useCheckIn` sends `note`; the toast says "Note posted" for a note alone.
- `JournalCard`: "Ana wrote" (`crew.journal.note`) for a note alone; any check-in card with a
  note shows it under the header line through `FeedCard`'s `note` (line breaks kept, long words
  wrap).
- i18n ro + en: `checkins.note`, `checkins.notePlaceholder`, `checkins.postNote`,
  `checkins.notePosted`, `crew.journal.note`.
- `docs/design-system.md`: the `FeedCard` row mentions the note; `/design` shows a card with one.

### Tests

- A note with the check-in, with a "+N", with files, alone after the check-in: each one post,
  one card with the note frozen in its facts.
- A note alone before the check-in: on a challenge without a number it is the check-in (B3); on
  one with a number it asks for the number.
- Over 500 characters refused; spaces only means no note; emojis (with skin tones and joined
  ones) come back exactly.
- A note alone on a challenge that asks for proof needs none; the check-in still does.
- Undo removes a note post and its card; refused once someone else commented.
- The journal's day counts do not change with note posts.
- Vitest: the card sends the note with a hold and with a chip; "Post note" shows only after the
  check-in; the note stays after an error. The journal card shows the note.
- e2e (`checkins.spec.ts`): check in with a note, then post a second note: two cards, each with
  its note.
- Seeds: one note in `seed_demo_history`.

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
| 0. Plan | This plan with the owner's answers; glossary: **Note**, and **Card** gains the failed window; AGENTS.md game rules: a post may carry a note, a failed window shows in the journal when its spins open | S |
| 1. Missed window card | Section 1: kind, writer in `open_spins` (one transaction), API, `FailedFeedCard`, tests, `make schema`; `docs/plans/journal.md` card table and `docs/architecture/api-conventions.md` kinds list gain `failed`; the demo crew shows one after `make seed` | S |
| 2. Notes | Section 2: column, rules, API, the note box, "Post note", the note on cards, tests, e2e, seed | M |
| 3. Short punishment texts | Section 3: `TruncatedText`, `usePopover` out of `ReactionMenu`, the four places, design docs and `/design`, tests | S |
| 4. Cleaning | See below | S |

Each stage: `make check` passes; stages 1 and 2 also `make e2e`. Each is safe to ship on its
own: an older app shows nothing for a `failed` card it does not know, and posts without `note`.

## Stage 4: cleaning

The three features read again as a whole, with the code around them, to leave it simpler and
correct.

**Where:** every file stages 1 to 3 touched, plus what they lean on: `apps/doom` (services,
selectors, tasks, tests), `apps/checkins/services.py` and `card_facts`, `apps/journal` (services,
selectors, API), `features/doom`, `CheckInCard`, `JournalCard`, `FeedCard`, `ReactionMenu`,
`ListRow`, the i18n files for the keys these use.

**Look for:**
- Dead code: functions, props, CSS classes, i18n keys and test helpers nothing uses; branches no
  caller reaches (for example the "files" wording paths once notes exist).
- Duplicates the new pieces should own: hand-written ellipsis CSS that `TruncatedText` covers,
  placement or dismissal code that `usePopover` covers, failure wording that `describeFailed`
  covers.
- Helpers used once that read better inline; names that no longer say what a thing does (e.g.
  "files" posts that may now carry a note).
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
| `docs/plans/missed-notes.md` (this), `docs/glossary.md`, `AGENTS.md` game rules | 0 |
| `docs/plans/journal.md` (card kinds), `docs/architecture/api-conventions.md` (kinds) | 1 |
| `docs/design-system.md` (`FeedCard` note) | 2 |
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

- Editing or deleting one note (only "Undo" of the latest post, as today).
- Notes when serving a punishment, on days the challenge does not ask for, or on past days.
- Missed cards for challenges without punishments.
- Notifications ("Ana missed the week"): after v1, with Web Push.
- Formatting, mentions or link previews in notes.
- Who watched a proof video (discussed separately; a plan of its own if wanted).
