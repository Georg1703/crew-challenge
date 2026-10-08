# Plan: Wheel of Doom, punishments and generic proofs

Status: planned (2026-10-08). One branch and one pull request per stage. Screens: design C
("The dial") on the design canvas (private, the owner's):
https://claude.ai/artifact/7UG7dkUWgTWXq3Mist9Xx9

Priorities, in order: a spin is owed exactly when a window failed and never twice, the draw is
fair and decided on the server, the crew sees every punishment, the code ends smaller per feature
than a copy would be (one proof model for everything).

## Goal

A participant who falls short of a challenge spins a wheel of punishments, does the punishment
and proves it. The crew sees each punishment in the journal.

1. A challenge has no punishments, or 2 to 8. Each says whether it needs proof.
2. When a window fails (stage 1 of the periods plan: `judge()`), the participant owes one spin per
   missing check-in, or one for a missed total.
3. Today shows a card while anything is owed. It opens the spins page: one card per spin, oldest
   first. Spinning turns a dial; the server has already drawn the result.
4. After the spin, the same card asks for proof (or a "Done" tap when the punishment needs none).
   The draw posts a journal item; its proofs attach to that item.

Also in this plan: a challenge's proof setting becomes yes or no (photo or video, no choice of
kind), and proofs get one generic model that check-ins and spins share.

## Scope change (v1)

`AGENTS.md` and `docs/design-system.md` list the Wheel of Doom as after v1. The owner moved it
into v1 on 2026-10-08. Stage 0 updates both, and the glossary rows that say "after v1" for
Punishment, Spin and Wheel of Doom. Wilted trees and Web Push stay after v1.

## Decisions (agreed 2026-10-08)

| Topic | Decision |
|---|---|
| Who writes punishments | The creator, in the proposal wizard; editable only while it is a proposal, like the rest (editing resets votes). |
| Running challenges | Not changed: a scheduled challenge cannot get punishments, so the production challenge never spins. |
| How many | None, or 2 to 8. One is refused (nothing to draw from). None means failed windows owe nothing. |
| Proof on a punishment | Yes or no. Yes: a photo or a video. No: the person taps "Done". |
| Proof on a challenge | Yes or no (`proof_required`). Yes: a photo or a video, with the nudge until one is added. No: no proof. Proof never changes whether a day is done. |
| Spins per failed window | One per missing check-in (1 of 3 -> 2 spins; a missed daily day -> 1); one for a missed total. |
| From when | Only challenges with punishments, which are all proposed after this ships: nothing for past misses. |
| Leaving | Spins already owed stay. The window cut by leaving is judged like any other (its need is scaled). |
| An unspun spin | Never expires; the Today card stays until it is spun. |
| Odds | Equal; the same punishment can come twice in a row. |
| Serving | Within 7 days of the draw (`serve_by`); after that the card says "Late". No other penalty in v1. |
| Today card | Shows while anything is owed ("2 spins - 1 proof to add"), right under the day ring card, above the challenge cards; at the top when there is no ring. |
| Journal | One item per spin, posted when drawn; its proofs attach to it and move it to the top, like a check-in's. The crew can react. Seen by the challenge's participants and admins. |
| Proofs on a spin | Same as check-ins: up to 5, photo or video, straight to storage, removable on the day they were added. Allowed any day until served. |
| Proof model | One generic `Proof` for any subject (a check-in, a spin), in its own app. |
| Screens | Design C: a dial (the day ring's shape) with one arc per punishment. |

## Words (glossary changes)

| Term | Code name | Meaning |
|---|---|---|
| Punishment | `Punishment` | One of a challenge's punishments: a short text and whether it needs proof. None, or 2 to 8, written by the creator; fixed once scheduled. Replaces "an entry in the crew's pool of forfeits". |
| Spin | `Spin` | One turn of the wheel owed for one missing check-in (or one missed total) in a failed window. Status (derived): `pending` (not spun), `spun` (drawn, not served), `served`. Replaces `PunishmentSpin`. |
| Draw | `doom.services.draw` | Choosing a spin's punishment, on the server, before the dial turns. |
| Serve by | `Spin.serve_by` | The last day to serve a spun punishment: the draw's day + 7. After it the spin is late. |
| Served | - | A spun punishment with a shown proof, or tapped "Done" when it needs no proof. |
| Proof | `Proof` | Kept, widened: a photo or video backing a subject (a check-in or a spin). |
| Proof subject | `Proof.subject` | What a proof backs, by a generic key (`subject_type` + `subject_id`). |
| Proof kind | `Challenge.ProofKind` | Removed: proof is yes or no. |

## The model (end state)

```
Challenge (challenges)
  proof_required  bool            yes: photo or video; no: no proof

Punishment (challenges; CrewScopedModel)
  challenge       FK              related_name "punishments"; none, or 2 to 8 per challenge
  position        smallint        1..8, the number on the dial; unique per challenge
  text            varchar(80)
  proof_required  bool            yes: photo or video; no: "Done"

Spin (doom; CrewScopedModel)
  challenge, member               FKs
  window_first, window_last       the failed window it came from
  number                          1..k within that window
  need, done                      the window's need and what was done (for "1 of 3")
  punishment      FK null         the drawn Punishment (PROTECT), set by the draw
  drawn_at        timestamptz null
  serve_by        date null       the draw's crew-local day + 7
  done_at         timestamptz null  "Done" on a punishment without proof
  proofs, reactions               GenericRelations
  unique (challenge, member, window_first, number)

Proof (proofs; table stays checkins_proof)
  member          FK               who added it (ownership checks)
  subject_type    FK ContentType   + subject_id uuid: a check-in or a spin
  kind, status, original, thumb, duration   as today
```

- Punishments are rows of their own. While the challenge is a proposal they are replaced as a
  whole with the rest of the shape (no spin can point at them yet); once scheduled they are frozen,
  and a spin points at the one it drew (`PROTECT`). The count (none, or 2 to 8) is checked in
  `clean_shape`; the database keeps `position` 1-8 and unique per challenge.
- A spin's status is derived, like verdicts: `served` = `done_at` set, or a shown (processing or
  ready) proof exists. Nothing to keep in sync when a proof is removed.
- Proof keeps its table name, so moving it to its own app is a state-only migration.
- A proof is removable on the crew-local day it was added. For a check-in that is the check-in's
  day, as today, so one rule covers both subjects and the proofs app needs no registry.

## How a spin happens

```
window closes (crew midnight)
  -> doom.open_spins (Celery beat, hourly, idempotent)
       for each chosen challenge with punishments, each participant (leavers too),
       each window with last < today: judge(); failed -> spins 1..k (k = missing check-ins,
       or 1 for a total); bulk insert, ignoring the ones that exist (unique constraint)
  -> Today: "2 spins" card -> /spins
  -> POST /spins/{id}/draw: lock, pick a punishment with secrets, set drawn_at and serve_by
       (repeat-safe: an already drawn spin comes back as it is) -> the dial lands on it
  -> journal item (the spin, drawn_at) for the crew
  -> proof needed: POST /spins/{id}/proofs (same upload as check-ins) -> served when shown
     no proof: POST /spins/{id}/done -> served
```

The task judges every closed window of the challenges it covers each hour. That is a few hundred
small judgements for a family crew; it gets a "last judged" marker if crews grow.

## API (end state)

| Request | What it does |
|---|---|
| `GET /api/v1/spins` | My open spins (pending, and spun but not served), oldest first, with the challenge, its punishments and my proofs; `to_spin`, `to_serve` counts for the Today card |
| `POST /api/v1/spins/{id}/draw` | Draw the punishment; returns the spin with its `punishment` (its `position` is where the dial lands) |
| `POST /api/v1/spins/{id}/done` | Serve a punishment that needs no proof |
| `POST /api/v1/spins/{id}/proofs` | Start a proof on a spun spin (same body and answer as check-in proofs) |
| `GET /api/v1/journal?cursor=` | The crew's journal: `{kind: "check_in" or "spin", activity_at, check_in or spin, day_summary}` |
| `PUT/DELETE /api/v1/reactions/spin/{id}` | Reactions on a spin's journal item (a new target) |
| `/api/v1/proofs/...` | Unchanged URLs (parts, complete, resume, delete), now in the proofs app |
| Challenge shape | `proof_required` (no `proof_kind`), `punishments` |

`GET /api/v1/feed` stays one release beside the journal so a phone with the previous app keeps a
working feed during a deploy, then goes (stage 6).

Errors (new codes): `spin_not_found` (404), `already_served` (409), `proof_not_needed` (409, proof
or "Done" on the wrong kind of punishment), `not_drawn` (409), `punishments_count` (validation,
1 punishment or more than 8).

## Screens (design C)

- **Today**: while anything is owed, a card right under the day ring card (above the challenge
  cards; at the top when there is no ring): the dial mark, "2 spins - 1 proof to add", one button
  "Open". Hidden otherwise. `TodayCheckIns` takes it as a slot from `HomeRoute`, so check-ins don't
  import the doom feature.
- **Spins page** (`/spins`), one card per open spin, oldest first:
  - pending: challenge chip, "Week September 28 - October 4: 1 of 3", the dial with one arc per
    punishment and the numbered list under it, button "Spin". The dial turns to the drawn position
    (skipped with reduced motion), then the card becomes the next state;
  - spun, proof needed: the punishment, "Serve by Wednesday, October 14" (or "Late"), proof tiles
    and the add tile (the same upload as check-ins);
  - spun, no proof: the punishment and a "Done" button;
  - served: the card leaves with a toast. Empty page: "Nothing to spin".
- **Journal**: a spin card: who, the challenge, the dial mark with the drawn arc, the punishment,
  its state (to serve, late, served), then its proofs as a mosaic and reactions.
- **Proposal wizard**: a "Punishments" step after proof: up to 8 rows (text, "Needs proof" toggle),
  add and remove; none is allowed, one is not. The proof step becomes one toggle.
- **Challenge page**: the punishments, numbered, with a proof mark.
- New shared component `Dial` (`shared/ui`): N arcs (2-8), a marker, the drawn arc highlighted;
  sizes for the card and the mark. Documented in `docs/design-system.md` and shown on `/design`.

## Stages

Each stage is one pull request, ends with `make check` green and is reviewed before the next.
Every migration works with the previous release still serving (see `docs/recipes/new-migration.md`):
columns go in two releases.

| Stage | Branch | What works at the end | Size |
|---|---|---|---|
| 0. Plan and scope | `docs/wheel-plan` | This plan; the wheel is in v1 in the docs | S |
| 1. Proof yes or no | `feat/proof-yes-no` | Challenges ask "Proof?" yes or no; photo or video always | S |
| 2. Generic proofs | `refactor/generic-proofs` | One `Proof` model in `apps/proofs` for any subject; check-ins use it; nothing changes for people | L |
| 3. Punishments | `feat/punishments` | The wizard asks for punishments; the challenge page shows them; old proof columns dropped | M |
| 4. Spins (backend) | `feat/spins` | Spins open when windows fail; draw, done, spin proofs, journal and reactions in the API | L |
| 5. Wheel screens | `feat/wheel-screens` | Today card, spins page with the dial, journal spin cards | L |
| 6. Clean-up | `chore/drop-old-feed` | The old feed endpoint is gone | S |

### Stage 0 - Plan and scope

- This plan.
- `AGENTS.md`: the wheel moves from "after v1" into the v1 list; the game rules say how spins are
  owed and served. `docs/design-system.md`: the Wheel of Doom leaves "Not in this version".
- Glossary: Punishment, Spin and Wheel of Doom as in "Words"; the other rows change in the stage
  that builds them (Proof and Proof subject in 2, Draw, Serve by and Served in 4).

### Stage 1 - Proof yes or no

- Backend: the challenge shape takes `proof_required` only; `clean_shape` drops `proof_kind`;
  `start_proof` accepts a photo or a video whenever the challenge asks for proof.
- Migration: data only, `proof_required = (proof_kind != 'none')`, so a challenge that took
  optional proof now asks for it. The `proof_kind` column stays one release, written by the new code
  as `photo_or_video` or `none` so the previous release reads it right during the deploy.
- Frontend: the wizard's proof step is one toggle; `describeProof` says "Photo or video" or "No
  proof"; the Today card and the add tile no longer read a kind (the picker sheet asks photo or
  video, as it already does for `photo_or_video`).
- Seeds: `seed_demo_challenge` and `seed_demo_history` use the boolean.
- Removed: `Challenge.ProofKind` from the shape and the API, `KINDS` in `checkins/services.py`,
  the `KINDS` map in `ProofRow.tsx`, i18n `challenges.describe.proof.{photo,video,photo_or_video}`
  and the wizard's kind options.
- Tests: the shape (old `proof_kind` input ignored), the data migration on each old value, a photo
  and a video accepted on a challenge with proof, both refused without.

### Stage 2 - Generic proofs

- New app `apps/proofs`: `Proof` moves here with a state-only migration (the table stays
  `checkins_proof`). New columns `member`, `subject_type`, `subject_id`, filled from the check-in;
  `check_in` becomes nullable and leaves the model (the column goes in stage 3).
- Services move with it and stop knowing check-ins: `start_proof(subject, member, kind, ...,
  expires_at, max_count)` (the caller checks its own rules and locks its subject row first),
  `resume_proof`, `sign_parts`, `record_part`, `complete_proof`, `delete_proof` (owner, on the day
  it was added), `finish_videos`, `expire_proofs`; the Celery tasks too. The views for
  `/api/v1/proofs/...` move with the same URLs.
- Check-ins become the first subject: `CheckIn.proofs` is a `GenericRelation`; the check-in start
  endpoint keeps its URL and its rules (today, checked in) and calls the generic service. The
  feed, the board, the day sheet and the Today card read proofs through the relation.
- `ProofUploadOut`: `subject` (`check_in`) and `subject_id` added; `challenge_id` and `day` kept
  for check-ins (resume uses them).
- import-linter: "Proofs know files and members, not challenges, check-ins or spins"; check-ins
  (and doom later) build on proofs.
- Frontend: `features/proofs` takes the upload engine, its store and `ProofRow` (as `ProofTiles`)
  from `features/checkins`; an upload is started by a `start(body)` function the caller passes, and
  tiles group by a subject key. Check-ins pass theirs.
- Docs: `docs/architecture/backend.md` (the app, its contract, "Generic building blocks"),
  `docs/plans/proof-upload.md` pointers, the glossary's Proof row.
- Tests: the existing proof tests move and keep passing unchanged in substance; the migration
  forward and back on a copy of the dev database (rows keep their files and subjects); ownership by
  `member`; a proof on an unknown subject type is refused.

### Stage 3 - Punishments

- `Punishment` model (challenge, position, text, proof_required) with a check constraint
  (position 1-8) and a unique key (challenge, position). `clean_shape`: none or 2-8 items, text
  1-80 characters (trimmed, no duplicates), `proof_required` boolean. `propose_challenge` and
  `update_proposal` write them; editing a proposal replaces them as a whole. The challenge API
  embeds them (`position`, `text`, `proof_required`).
- Wizard step "Punishments" after "Proof"; the challenge page lists them; the proposal summary
  says how many.
- Migrations that finish earlier stages (the previous release no longer reads these columns):
  drop `challenges_challenge.proof_kind`; fill `subject` again for proofs started during the stage 2
  deploy, make it required, drop `checkins_proof.check_in_id`.
- Removed: the `proof_kind` column, the proof's `check_in` column.
- Tests: the shape (0, 1, 2, 8, 9 items; blank, long and repeated texts), the constraints, editing
  a proposal replaces its punishments and resets its votes, a scheduled challenge's punishments
  cannot change, deleting a proposal deletes them.

### Stage 4 - Spins (backend)

- New app `apps/doom` (named in `backend/AGENTS.md`): `Spin`, services `open_spins` (beat, hourly),
  `draw`, `serve_without_proof`, `start_spin_proof`; selectors `open_spins_of(member)`,
  `journal_spins(member)`, `reactable_spin`; registered as a reaction target (`spin`) and a proof
  subject (`GenericRelation`).
- Journal: `checkins/journal.py` holds a small registry of journal sources (check-ins register
  themselves, doom registers spins), like reaction targets: each source gives its items' ids and
  `activity_at` for the member; `GET /api/v1/journal` merges them in one cursor-paged query and
  loads each page per source. `day_summary` stays the check-ins' (spins show as their own cards).
- import-linter: doom builds on check-ins and proofs; nothing below imports doom.
- Tests:
  - opening: a failed week opens one spin per missing check-in, a missed total opens one, a met
    window none, a challenge without punishments none; running twice opens nothing new; the window
    closes at crew midnight (23:59 / 00:01) and on the DST day (October 25, 2026); a leaver's cut
    window; windows after the challenge ended;
  - drawing: only my own pending spin; repeat-safe; equal odds (many draws with a seeded random
    source); `serve_by` = draw day + 7 in the crew's time zone; late after it;
  - serving: a shown proof serves it, removing it un-serves it; "Done" only without proof; proofs
    only on a drawn spin that needs them, at most 5;
  - journal: spins appear when drawn, ordered with check-ins by activity, visible to participants
    and admins only; reactions on a spin item.

### Stage 5 - Wheel screens

- `shared/ui/Dial` (with its states and reduced motion), on `/design` and in the design system.
- `features/doom`: `useSpins`, the Today card, the `/spins` route with its three card states,
  `useDraw` (optimistic: the dial starts at once and lands when the answer comes), "Done".
- Journal: `CrewFeed` reads `/api/v1/journal` and renders spin cards (`FeedCard` gains the spin
  kind); reactions on them.
- i18n (ro and en): the Today card, the spins page, the wizard step, the journal card, the errors.
- e2e: a seeded failed week -> Today card -> spin -> proof photo -> journal shows it served.

### Stage 6 - Clean-up

- Removed: `GET /api/v1/feed`, `FeedView`, `useFeed` and its test fixtures (the journal replaced
  them a release ago).

## Removal checklist

| Item | Where | Stage |
|---|---|---|
| "After v1" for the wheel, punishments and spins | `AGENTS.md`, design system, glossary | 0 |
| `Challenge.ProofKind` in the shape and API, `KINDS`, kind i18n keys and wizard options | backend, frontend | 1 |
| Proof services, views, tasks and tests in `apps/checkins` | backend | 2 |
| `Proof.check_in` in the model | backend | 2 |
| `features/checkins/uploads`, `ProofRow` | frontend | 2 |
| `proof_kind` and `checkins_proof.check_in_id` columns | migrations | 3 |
| `GET /api/v1/feed`, `FeedView`, `useFeed` | backend, frontend | 6 |

## Out of scope

Punishments on a running challenge, an admin forgiving a spin, weighted odds, "spin all", wilted
trees, Web Push reminders, proof that decides whether a day is done, excused days.

## Risks

| Risk | Answer |
|---|---|
| Moving `Proof` to a new app breaks data | State-only move, same table; additive columns; run forward and back on a dev database copy; the drop waits a release. |
| A spin owed twice, or not at all | The unique key (challenge, member, window, number) and an idempotent task; tests at midnight, on the DST day and for leavers. |
| The draw is guessable or changed by the phone | Drawn with `secrets` on the server before any animation; the phone only animates to the answer. |
| Many spins after a bad month on a daily challenge | That is the rule (one per missed day); the page lists them all. "Spin all" is a later idea. |
| Old app during a deploy | The old feed endpoint stays one release; new fields are additive. |
