# Plan: viewers on a challenge

Status: agreed with the proposed defaults (2026-10-12); stages 1 and 2 built. Three stages after
the plan, on one branch (`feat/viewers`), one commit per stage, each committed after the owner's
review.

## Goal

A crew member can follow a challenge without taking part: a **viewer** sees the challenge, its
board, the day sheets and its journal cards, and reacts and comments like anyone else, but has no
check-ins, no streak, no day on the board, owes no spins and does not count toward "the whole
crew finished the day". A grandparent who wants to see what is up; a member who left and still
wants to watch.

## What changes for members

| | Today | After |
|---|---|---|
| Proposing: the "who" step | A checklist: takes part or not | Each person: takes part, watches, or nothing (the creator always takes part) |
| Challenge page | "Taking part: ..." | "Taking part: ..." and, when any, "Watching: ..." |
| A viewer's challenge page | - | The board and the day sheets as an admin sees them; no vote, no check-in card, a note "You watch this one; you don't take part"; "Stop watching" instead of "Leave" |
| Today and Echipa | - | A viewer's day has nothing from this challenge (no card, no ring segment, not in the crew's day) |
| Journal | - | A viewer sees the challenge's cards and reacts and comments on them |
| Leaving a running challenge | The challenge disappears for you | A switch on the leave sheet: "Keep watching" (default off) |

## Decisions

Proposed defaults, to confirm:
- A viewer does not vote. Votes say who wants to do the challenge; a viewer will not do it.
  (The `not_a_participant` error already covers it.)
- Only the creator makes someone a viewer, in the "who" step, until the challenge is scheduled
  (the same rule as for participants). Nobody joins a challenge on their own, as today.
- A viewer stops watching whenever they like (the row goes, before or during the challenge);
  they cannot come back on their own, as a participant who opted out cannot.
- A participant who opts out or leaves can keep watching: the same row becomes a viewer's
  (`role = viewer`; `left_on` stays, so the board keeps their days and the wheel still judges
  the cut window).
- Viewers are not on the board, the day sheet, the member page or the crew's day; they are a
  separate line on the challenge page. An admin who is in neither list sees everything, as today.
- The creator cannot be a viewer of their own challenge.
- No cap, no notification, no "viewer" on the crew level: it is per challenge.

## Model

One column on `Participant`, no new table:

```
Participant
  role  "player" (default) | "viewer"
```

- `visible(member)`: rows where `left_on` is null OR `role = viewer` (a leaver who kept
  watching). Admins see everything, as today.
- "Takes part" (check-ins, votes, the board, `participants_on`, `crew_day`, `member_progress`,
  `open_spins`, `card_facts`, the seeds) adds `role = player` to its filter. One helper in
  `challenges/selectors.py` (`players(...)`) so the filter is written once.
- Glossary: **Viewer** - a member who follows a challenge without taking part (`Participant`
  with `role = viewer`); sees it, reacts and comments, no check-ins, no vote, no spins.

## API

```
POST /api/v1/challenges                 ChallengeIn gains viewer_ids (optional, default none)
PUT  /api/v1/challenges/{id}            same
PUT  /api/v1/challenges/{id}/participants   {participant_ids, viewer_ids}
GET  /api/v1/challenges...              ParticipantOut gains role; taking_part stays
                                        "a player who has not left"; new watching: bool
DELETE /api/v1/challenges/{id}/participation?keep_watching=true
                                        opt out or leave, and stay as a viewer (viewers: the row goes)
```

- A member in both lists: `ValidationFailed` on `viewer_ids`.
- `GET /today`, the board, the day sheet, `/members/{id}/progress`: unchanged shapes; viewers
  are simply absent.

## Rules in services

- `_set_participants(challenge, member_ids, viewer_ids)`: the creator is always a player;
  someone moved from player to viewer loses their vote (as when removed); someone moved from
  viewer to player keeps nothing (they had no vote).
- `cast_vote`: players only (`NotAParticipant` for a viewer).
- `_lock` (who sees the challenge): any row in `visible`, admins too, unchanged.
- `stop_taking_part(by, keep_watching)`: a viewer's row is deleted whatever the phase; a
  player's row is deleted (before the start) or gets `left_on = today` (during), and with
  `keep_watching` it is kept with `role = viewer` instead of deleted / hidden.
- Check-in gate `_participant`: players only (`NotTakingPart` for a viewer).
- `crew_day`: viewers are never due.
- `open_spins`: players only (a leaver who kept watching still owes the cut window: the row
  is a player's by `left_on`, so the role filter must be `role = player OR left_on set`;
  simpler: judge rows with `left_on` set or `role = player`).

## Frontend

- `ParticipantPicker`: the "takes part" checklist as today, and under it a second checklist,
  "Only watching", of the people not taking part (built, instead of a three-way row: two
  existing components, nothing new). The Review step lists the watchers.
- `ChallengeRoute`: a "Watching" `ParticipantList` under "Taking part"; for a viewer the vote
  button hidden, the note `challenges.who.watching`, the button "Stop watching"
  (`challenges.stopWatching`) with its confirm sheet; for a player the leave sheet gains the
  "Keep watching" switch.
- `PoolProposals`, `ProposalsRow`: "waiting for your vote" counts proposals where
  `taking_part` (today it counts all visible ones: a viewer and an admin would see a count for
  proposals they cannot vote on).
- i18n (ro + en): `challenges.who.watches`, `challenges.who.watching`,
  `challenges.watchingTitle`, `challenges.stopWatching`, `challenges.stopWatchingTitle/Body`,
  `challenges.keepWatching`, `challenges.facts.watchers`.

## Stages

| Stage | What works at the end | Size |
|---|---|---|
| 0. Plan | This plan, the glossary entry, AGENTS.md game rules | S |
| 1. Backend | `role` column and migration; `players()` helper and every "takes part" read on it; `viewer_ids` on create, edit and the participants endpoint; `keep_watching`; `role` and `watching` in the output; tests for seeing, voting, checking in, the board, the crew's day, spins and leaving-as-viewer; `make schema`; one viewer in `seed_demo_history` | M |
| 2. Frontend | The three-way picker; the "Watching" list; the viewer's challenge page; "Stop watching"; "Keep watching" on the leave sheet; the vote count fix; e2e: the creator makes Dan a viewer, Dan sees the board and has no card on Today | M |
| 3. Cleaning | Every file stages 1 and 2 touched, read again with the feature whole: dead code, branches no caller reaches, helpers used once, flags and fields nothing reads, repeated filters that `players()` should own, comments that restate the code, tests that cover the same thing twice. Deletions and merges only; behaviour and the API stay as stage 2 left them; `make check` and `make e2e` still green | S |

## Out of scope

- A viewer asking to join, or a player asking to watch, after scheduling (nothing changes
  once scheduled, as today).
- Crew-level "viewer" members (someone who never takes part in anything): a crew member who is
  a viewer on every challenge covers it for now.
- Notifications to viewers (after v1, with Web Push).
