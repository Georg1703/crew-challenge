# Plan: adding people to a challenge at any time

Status: agreed with the proposed defaults (2026-10-22). Built on one branch (`feat/joined-on`)
as one commit (the owner's choice), committed after the owner's review.

## Goal

The creator or a crew admin can add someone to a challenge at any point until it ends: before
the start (as today, but also after scheduling) or while it runs. Someone added while it runs
takes part from that day: earlier days are not theirs, so they are never missed, never break a
streak and never owe a spin. A new crew member, a kid who changed their mind, a viewer who now
wants in.

## What changes for members

| | Today | After |
|---|---|---|
| Who changes the lists | The creator, while it is a proposal | Same, and once scheduled the creator or an admin can still add people, until the last day |
| Scheduled, not started | Put it back in the pool, edit, schedule again | "Add people" on the challenge page; they take part from the start |
| Running | Nobody can be added | "Add people": they take part from today |
| A viewer | Watches until the end | Can be made a participant (from today) |
| The board | Days before the start are outside | A late joiner's days before they joined are outside too (grey, not missed) |
| Board row | "left on 12 Oct" under a leaver | Also "joined on 15 Oct" under a late joiner |

## Decisions

Proposed defaults, to confirm:
- Who adds after scheduling: the creator or any crew admin (an admin may need to add a new crew
  member while the creator is away). Before scheduling: the creator only, as today.
- Who can be added: a crew member not in the challenge, or a viewer (who becomes a
  participant). Someone who left cannot come back, as today. People who join the crew later are
  still not added on their own: someone adds them.
- First day: the day they are added counts (crew time zone), the mirror of `left_on` (the day
  someone leaves still counts). Added before the start: they take part from the start and
  `joined_on` stays empty.
- Their first window (a week, a month or the whole period) is cut to their days and its need
  scaled down in proportion, the rule `apps/challenges/windows.py` already applies to a late
  start or to leaving. Nothing new to decide there.
- Once scheduled, the lists only grow: nobody is removed and nobody is turned into a viewer by
  the creator (people still leave on their own, as today). Adding viewers stays allowed.
- No vote for someone added after scheduling (votes end at scheduling).
- No journal card and no notification for a join (see Out of scope).

## Model

One column on `Participant`, no new table:

```
Participant
  joined_on  date, null   first day that counts, when the member was added during the challenge
```

- Empty means "from the start" (every row today, and everyone added before the start). The
  migration only adds the nullable column; no data migration.
- `days.span(challenge, participant)` takes the row instead of `left_on` and starts at
  `max(start_date, joined_on)`. Every caller already has the row: `doom.services`, the four in
  `checkins.selectors`, `seed_demo_history`. The one that passes `None` today (own progress in
  `checkins.selectors`) passes the member's row.
- The "takes part on these days" filter, today written three times as
  `Q(left_on__isnull=True) | Q(left_on__gte=day)` (`participants_on`, member progress,
  `crew_day`), becomes one helper next to `PLAYS` in `challenges/selectors.py`, `on_days(first,
  last)`, that also checks `joined_on`. Written once now that it has two halves.
- Glossary, Participant: "... leaving during it sets `left_on`; someone added during it gets
  `joined_on` (their first day)."

## API

```
PUT /api/v1/challenges/{id}/participants   {participant_ids, viewer_ids}   unchanged shape
GET /api/v1/challenges...                  ParticipantOut gains joined_on (date or null)
```

- While a proposal: as today (the creator only, any change).
- Once scheduled, until the end date: the creator or an admin. The request keeps every current
  row; new ids become rows (players get `joined_on = today` after the first day, null up to
  it: on the first day they simply start with everyone); a viewer moved into `participant_ids`
  becomes a player the same way. Removing someone, making a player a viewer, or adding someone who
  left: `participants_locked`. After the end date: `challenge_finished` (exists).
- `PUT /api/v1/challenges/{id}` (editing the proposal) stays proposal-only.

## Rules in services

- `set_participants`: `_require_proposed` becomes "proposed, or chosen and not finished"; the
  creator check admits admins once chosen; for a chosen challenge `_add_participants` checks the
  request only adds, then creates rows (and flips viewers) with `joined_on` as above. The
  proposal path (`_set_participants`) is unchanged.
- Check-in gate, posts, undo: unchanged (today is in a joiner's span from the day they join).
- `open_spins` / the doom job: unchanged code; the span starts at `joined_on`, so no window
  before it exists, and the cut first window is scaled.
- `crew_day`: someone who joined today is due today; before that, not.

## Frontend

- `ChallengeRoute`: an "Add people" button (`challenges.who.add`) for the creator or an admin on
  a scheduled challenge that has not ended. It opens `ParticipantsSheet` in add mode.
- `ParticipantsSheet` / `ParticipantPicker`: the picker gains `locked` (the lists as they are:
  they can only grow) next to `creatorId`. In add mode every current player is locked in, every
  viewer is locked in the watch list but can be ticked to take part, and people who left are
  not shown (`pickedFrom` leaves them out of the lists). The note says they take part from today
  (`challenges.who.addNote`) or, before the start, from the start (`challenges.who.addNoteBefore`).
- Board: a `joinedOn` map next to `leftOn` for the row's "joined on 15 Oct" note; the days
  before it already come from the server as outside. (No subtitle on the participant list: it
  only lists players before the start, when nobody has `joined_on`.)
- i18n (ro + en): `challenges.who.add`, `challenges.who.addNote`, `challenges.who.addNoteBefore`,
  `checkins.board.joined`, `errors.participants_locked`.

## Tests

- Backend: added on day 15 of a monthly challenge -> days 1-14 outside, no missed days, no
  spins for them; a weekly count window cut on Wednesday asks for the scaled need; added today
  and checks in today -> counts; added at 23:59 and at 00:01 crew time (two different first
  days), one of them across a DST switch; a viewer made a participant; removing, demoting or
  re-adding a leaver -> `participants_locked`; after the end -> `challenge_finished`; an admin
  who is not the creator can add, another member cannot.
- Seeds: one late joiner in `seed_demo_history`.
- Frontend: the add sheet locks players and lets a viewer start playing; e2e: an admin adds Dan
  to a scheduled challenge and Dan then sees it as a participant. (A running challenge cannot be
  made from the UI in a test, since a start is tomorrow at the earliest; the backend tests cover
  the running case: today counts, earlier days outside, the scaled first window, spins.)

## Stages

| Stage | What works at the end | Size |
|---|---|---|
| 0. Plan | This plan, the glossary entry, the game rules in `AGENTS.md` | S |
| 1. Backend | `joined_on` column and migration; `span(challenge, participant)`; `on_days` helper replacing the three filters; adding after scheduling in `set_participants`; `joined_on` out; admin field; tests above; `make schema`; the seed | M |
| 2. Frontend | "Add people" and the sheet's add mode; `locked` in the picker; "Joined on"; `joinedOn` on the board; i18n; tests and the e2e | M |
| 3. Cleaning | Every file stages 1 and 2 touched, read again with the feature whole: dead code, helpers used once, repeated filters `on_days` should own, comments that restate the code, tests that cover the same thing twice. Deletions and merges only; behaviour and the API stay as stage 2 left them; `make check` and `make e2e` still green | S |

## Out of scope

- A journal card "Ana joined the challenge" (cheap later: one more card kind).
- A member asking to join on their own; joining is done by the creator or an admin.
- Removing someone during the challenge (they leave on their own, as today).
- Letting someone who left come back (two spans per row; not needed now).
- Notifying the person added (after v1, with Web Push).
