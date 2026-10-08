# Plan: Wheel of Doom, punishments and generic proofs

Status: stages 0-5 on `feat/wheel-of-doom` (2026-10-08); stage 6 ships in a later deploy. One branch for the whole plan, one
commit per stage, committed after the owner's review. Screens: design C
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
| Proofs on a spin | Same as check-ins: up to 5, photo or video, straight to storage, removable on the day they were added. Any day; the first one the crew can see serves it. |
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
  -> doom.open_spins (Celery beat, every 15 minutes, idempotent)
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

The task judges every closed window of the challenges it covers on each run. That is a few
hundred small judgements for a family crew; it gets a "last judged" marker if crews grow.

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

Errors (new codes): `spin_not_found` (404), `not_drawn` (409), `proof_needed` (409, "Done" on a
punishment that needs proof), `proof_not_needed` (409, a proof on one that does not). The count
of punishments is a field error (`punishments`) of `validation_failed`.

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

Each stage is one commit on `feat/wheel-of-doom`, ends with `make check` green and is reviewed
before it is committed (the branch names below were the first idea).
Every migration works with the previous release still serving (see `docs/recipes/new-migration.md`):
columns go in two releases.

| Stage | Branch | What works at the end | Size |
|---|---|---|---|
| 0. Plan and scope | `docs/wheel-plan` | This plan; the wheel is in v1 in the docs | S |
| 1. Proof yes or no | `feat/proof-yes-no` | Challenges ask "Proof?" yes or no; photo or video always | S |
| 2. Generic proofs | `refactor/generic-proofs` | One `Proof` model in `apps/proofs` for any subject; check-ins use it; nothing changes for people | L |
| 3. Punishments | `feat/punishments` | The wizard asks for punishments; the challenge page shows them | M |
| 4. Spins (backend) | `feat/spins` | Spins open when windows fail; draw, done, spin proofs, the journal and reactions in the API | L |
| 5. Wheel screens | `feat/wheel-screens` | Today card, spins page with the dial, journal spin cards | L |
| 6. Clean-up | `chore/drop-old-feed` | The old feed endpoint and the old proof columns are gone; deployed a release after 1-5 | S |

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

### Stage 2 - Generic proofs - done

- New app `apps/proofs`: `Proof` moves here without copying the table (still `checkins_proof`).
  Checkins `0004_proof_subject` adds `member`, `subject_type`, `subject_id` (nullable for a
  release) and lets `check_in` be empty; `0005_move_proof` fills them from the check-in and hands
  the model over; proofs `0001` is state only. Two check-in migrations because Postgres refuses to
  alter a table with updates pending in the same transaction (going back hit it).
- Services move with it and stop knowing check-ins: `start_proof(member, subject, kind, ...,
  expires_at)` (the caller checks its own rules and locks its subject row first),
  `resume_proof(by, fingerprint, subjects)`, `sign_parts`, `record_part`, `complete_proof`,
  `delete_proof` (owner, on the day it was added), `discard_files`, `finish_videos`,
  `expire_proofs`; the Celery tasks too (beat names now `apps.proofs.tasks.*`; a message queued
  under an old name during the deploy is dropped, and beat runs again in seconds). Parts, complete
  and delete keep their URLs.
- Check-ins become the first subject: `CheckIn.proofs` is a `GenericRelation`; the check-in start
  endpoint keeps its URL and its rules (today, checked in) and calls the generic service. The
  feed, the board, the day sheet and the Today card read proofs through the relation.
- Resume belongs to the subject: `GET /api/v1/challenges/{id}/check-ins/proofs/resume` looks at
  my check-ins of that challenge (so a file picked again after midnight still resumes yesterday's
  upload within its grace). `GET /api/v1/proofs/resume` is gone (a previous app gets 404 and starts
  a new upload), and `ProofUploadOut` lost `challenge_id` and `day` (nothing needs them now).
- import-linter: "Proofs know files and members, not challenges, check-ins or spins"; check-ins
  (and doom later) build on proofs.
- Frontend: `features/proofs` takes the upload engine, its store, the proof helpers and `ProofRow`
  (as `ProofTiles`) from `features/checkins`. A caller passes a `ProofSubject` (`key`, `start`,
  `resume`); tiles group this phone's uploads by its key. Check-ins pass `checkInProofs(challenge,
  day)`.
- Docs: `docs/architecture/backend.md` (the app, its contract, "Generic building blocks"),
  `docs/plans/proof-upload.md` pointers, the glossary's Proof row.
- Tests: the existing proof tests pass against the moved code; resume stays on its own challenge
  and works after midnight; the tile tests moved to `features/proofs`. The migrations ran forward
  and back on a scratch database with a proof (filled, a new row without `check_in`, restored).

### Stage 3 - Punishments - done

- `Punishment` model (challenge, position, text, proof_required) with a check constraint
  (position 1-8) and a unique key (challenge, position). `clean_shape`: none or 2-8 items, text
  1-80 characters (trimmed, no duplicates ignoring case), `proof_required` boolean.
  `propose_challenge` and `edit_proposal` write them (migration `0015_punishments`); editing a
  proposal replaces them as a whole and, when they changed, resets the votes. The challenge API
  takes and returns them (`position`, `text`, `proof_required`); lists load them in one query. The
  admin shows them read only.
- Wizard step "Punishments" after "What proof?" (design D3: a card per punishment with its text,
  "Needs a photo or video" and remove; "Add a punishment" up to 8; "2 of 8"); it refuses a single
  one, a blank one and repeats before moving on. The summary says how many; the challenge page
  lists them, numbered, with how each is served.
- The old columns (`proof_kind`, the proof's `check_in`) were to go here; they move to stage 6.
  The branch may be deployed in one go, and then the release before it (main) still reads them
  during the deploy: they can only go in a later deploy.
- Tests: the shape (0, 1, 2, 8, 9 items; blank, long and repeated texts), the database constraints,
  editing replaces them and resets votes only when they changed, a scheduled challenge cannot be
  edited, the API round trip; the wizard step (one is refused, two are sent) and the list.

### Stage 4 - Spins (backend) - done

- New app `apps/doom` (named in `backend/AGENTS.md`): `Spin` (migration `0001_initial`), services
  `open_spins` (beat every 15 minutes), `draw` (takes an `rng` for tests), `mark_done`,
  `start_proof`, `resume_proof`; selectors `owed` (my open spins and the counts), `mine`,
  `journal`, `reactable_spin`, `state`, `late`; a reaction target (`spin`) and a proof subject
  (`GenericRelation`, `related_query_name="spin"`). Locks use `select_for_update(of=("self",))`
  (Postgres refuses to lock the empty side of the outer join to the punishment).
- Journal: its own app, `apps/journal`, not a registry in check-ins: its API schema has to name
  both item shapes, and check-ins may not import the wheel. Each kind pages its own rows after the
  cursor (`activity_at`, id), the page is merged in Python (Django cannot filter a union), and
  `GET /api/v1/journal` answers `{kind, activity_at, check_in | spin}`. Check-in items are the
  feed's (`feed_items`, now shared with `/feed`); spin items carry the punishment, the number of
  arcs, the state, `serve_by`, late, shown proofs, reactions and the day's summary.
- import-linter: doom builds on check-ins and proofs, the journal on doom; nothing below imports
  either.
- Seed: two demo challenges (`seed_demo_history`) have punishments, so local data owes spins.
- Tests:
  - opening: a failed week opens one spin per missing check-in, a missed total opens one, a met
    window none, a challenge without punishments none; running twice opens nothing new; the window
    closes at crew midnight (23:59 / 00:01) and on the DST day (October 25, 2026); a leaver's cut
    window; windows after the challenge ended;
  - drawing: only my own pending spin; repeat-safe; the pick comes from the random source (equal
    odds are `random.choice`'s); `serve_by` = draw day + 7 in the crew's time zone; late after it;
  - serving: a shown proof serves it, removing it un-serves it; "Done" only without proof; proofs
    only on a drawn spin that needs them; resume on its own spin;
  - journal: spins appear when drawn, ordered with check-ins by activity, visible to participants
    and admins only; reactions on a spin item.

### Stage 5 - Wheel screens - done

- `shared/ui/Dial`: the day ring's shape cut into 2-8 numbered arcs, a marker that turns to the
  drawn arc (motion preset `dialTurn`, 3.6 s; at once with reduced motion or when already drawn)
  and lights it when it stops; `size="sm"` is a mark. Tokens `--dial-size`, `--dial-size-sm`.
  On `/design` and in the design system.
- `features/doom`: `useSpins`, `useDraw` (the button waits for the server's draw, then the dial
  turns), `useDone`, `spinProofs` (a `ProofSubject`); `SpinsCard` on Today, right under the day
  ring (`TodayCheckIns` takes it as `afterRing` from `HomeRoute`); `/spins` with a card per spin:
  what failed, the dial and the numbered punishments, then the punishment with "Serve by" (or
  "Late") and the proof tiles or "Done"; an empty state.
- Journal: `CrewFeed` and the crew page read `/api/v1/journal` (`useJournal`; `useFeed` is gone,
  the backend's `/feed` stays for a previous app); spin cards use `FeedCard` as it is (the drawn
  number as its highlight, the punishment as its line), with proofs and reactions.
- i18n (ro and en): the spins card and page, the journal card, the new error codes.
- Seed: `seed_demo_spins` (in `make seed`, `make setup` and the e2e server) gives the demo crew
  "Roata (demo)" whose last week owes three spins each; every run starts over.
- e2e (`e2e/spins.spec.ts`): Today card -> spins -> spin -> "Gata" -> the crew's journal shows it
  served. Proof uploads on a spin share the engine the proof e2e already covers.

### Stage 6 - Clean-up

- Deployed only after stages 1-5 are live (a release later), because the release before them
  still reads what this removes.
- Removed: `GET /api/v1/feed` and `FeedView` (the journal replaced them a release ago; the app
  stopped calling them in stage 5).
- Migrations: drop `challenges_challenge.proof_kind`; fill `member` and `subject` again for proofs
  the old release started during the deploy (raw SQL from `check_in_id`), then, in a migration of
  its own, make them required and drop `checkins_proof.check_in_id`.

## Removal checklist

| Item | Where | Stage |
|---|---|---|
| "After v1" for the wheel, punishments and spins (done) | `AGENTS.md`, design system, glossary | 0 |
| `Challenge.ProofKind` in the shape and API, `KINDS`, kind i18n keys and wizard options (done) | backend, frontend | 1 |
| Proof services, views, tasks and tests in `apps/checkins` (done) | backend | 2 |
| `Proof.check_in` in the model (done) | backend | 2 |
| `features/checkins/uploads`, `ProofRow` (done) | frontend | 2 |
| `proof_kind` and `checkins_proof.check_in_id` columns | migrations | 6 |
| `useFeed` (done) | frontend | 5 |
| `GET /api/v1/feed`, `FeedView` | backend | 6 |

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
