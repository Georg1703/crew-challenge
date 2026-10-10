# Plan: posts and a journal of frozen cards

Status: proposed (2026-10-10, reviewed the same day), not started. Six stages after the plan, plus
an optional seventh, each its own branch and pull request, deployed in order; each works on its
own and with the release before it still serving (`docs/recipes/new-migration.md`). Committed
after the owner's review.

Priorities, in order: a card shows what happened when it was posted and never changes after
(only its reactions, and later its comments); a card exists exactly when its post does (same
transaction); a check-in on a challenge that asks for proof is posted with that proof; less code
at the end than at the start; a journal page costs the same with 100 cards or 100,000.

## Goal

Everything a member does in a challenge is a **post**: a check-in, a "+N", proofs added later, a
punishment served. Photos and videos are picked and uploaded first, as draft files; the button
that posts them is available once they have all finished. Each post is one **card** in the
crew's journal (`JournalEntry`), written once with what it said at that moment. Cards are
added or deleted, never edited, so reactions and comments always belong to exactly what people
saw.

## What changes for members

| | Today | After |
|---|---|---|
| Check in, challenge asks for proof | Tap "Done", then "Add a photo or video" (a nudge, optional) | Pick 1 to 5 photos or videos; "Check in" becomes available when they have finished uploading |
| Check in, no proof asked | Tap "Done"; no photos possible | Tap "Check in" (posted at once), or pick files first: then "Check in" waits for them |
| "+N", challenge asks for proof | Type the number; proof optional, on the day | Type the number and pick its proof; "Add" waits for the uploads; every "+N" has its own |
| "+N", no proof asked | Type the number; no photos possible | The same, photos or videos optional; "Add" waits for any picked |
| Add proof later | Adds tiles to the day's card (the card rises); only where proof is asked | "Add photos or videos" on any challenge, then "Post" when uploaded: a new card, "Ana added 2 photos" |
| A file fails or is stuck | - | Retry it or remove it; the button waits only for the files still there |
| Remove a photo before posting | - | Remove it from the draft |
| Remove a blurry photo after posting | Delete the proof, the same day | Delete the post (your latest, today) and post again |
| Undo | Removes the day's last entry | The same: deletes your latest post of today |
| Serve a punishment that needs proof | Add a photo or video; the first one serves it | Pick 1 to 5; "Serve" becomes available when they have finished uploading |
| The journal | One card per check-in that grows; plain ones grouped; the crew's day added by the app | One card per post, frozen; every card takes reactions |

## Decisions

Agreed (2026-10-10):
- A card never changes after it is posted; only its reactions (and later comments) do.
- On a challenge that asks for proof, a check-in cannot be posted without at least one photo or
  video; that holds for every "+N" too.
- Any check-in or "+N", on any challenge, may carry 1 to 5 photos or videos. On a challenge that
  asks for proof they are required: no post without at least one. Elsewhere they are optional.
- Proofs added to a check-in later make a new post, with a card of its own (any challenge).
- A posted card keeps its proofs: to remove one, delete the post (same day) and post again.
- No grouping: every check-in is its own card. Every card takes reactions, the crew's day too.
- On every challenge, while picked files upload, the button that posts them ("Check in", "Add",
  "Post", "Serve") is not available; the member posts once they have all finished. A video still
  converting then shows "Preparing" on its card until it plays (the media loading, not the card
  changing).
- The plan is staged: stages well separated, each shipped on its own.

With a proposed default (confirm or change):
1. **A card's facts are stored with it** when it is posted (`JournalEntry.facts`, JSON written
   once). Read live: who people are (name, avatar), the media (signed links, "Preparing"),
   reactions and comments. A punishment reworded in the admin changes only later cards.
2. **Only your latest post of today can be deleted** (today's undo, kept). Deleting an earlier
   one would make the later cards' frozen totals wrong ("+3, 8 of 10" after the "+5" went).
3. **Cards say less**: the action, the amount and the day's total, the target, the streak and a
   milestone, how many proofs. The week strip and "day 12 of 30" leave the card: with a card per
   post they repeat on every "+N", and the board already shows the weeks.
4. **The crew's day counts the whole crew** on the challenges judged day by day (as today's
   card), whatever the viewer can see. The card names no challenge, so nothing leaks. A day with
   only weekly or monthly challenges has no such card.
5. **Writes are synchronous**, in the poster's transaction (see "Sync or async").
6. **Existing reactions move to their cards** (a check-in's to its first post's card, a spin's to
   its drawn card). History keeps its check-ins without proof; the rule holds from stage 2.
7. **Cards are written before they are read** (stage 4 before stage 5): production fills the
   table for a release while the app still shows the old journal, so they can be compared.
8. **Reactions point at cards with a plain foreign key** (optional stage 7): once every reaction
   is on a card, the generic target registry is flexibility nobody uses.

## The end state

### Posts

```
CheckIn                 one member, one challenge, one day (the day's verdict, as today)
  status                done | in_progress | pending (new: only draft files so far)
  amount                the sum of its "+N"s
  proofs                as today: every file of the day, posted or draft

CheckInEntry            one post (today: one tap or one "+N"; now also files added later),
                        unchanged: whether it counts follows from what it is (a "+N" has an
                        amount; on a "just check in" or "held" day the first post is the
                        check-in), so nothing new is stored

Proof
  post_id     new, null the post that published it (a CheckInEntry, or the spin it served);
                        empty: a draft file, seen by its owner only

Spin
  done_at               now "served at": "Done", or its photos and videos posted (kept, not
                        renamed: served is done)
```

The endpoints stay; only their rules change:

```
POST   /api/v1/challenges/{id}/check-ins/{day}/proofs  a draft file (any challenge; before the
                                                       check-in too: the day's check-in is then
                                                       made, pending)
POST   /api/v1/challenges/{id}/check-ins               post: a tap or a "+N" with the day's draft
                                                       files, or only the files (counts nothing)
DELETE /api/v1/challenges/{id}/check-ins/{day}/last    undo: my latest post of today
DELETE /api/v1/proofs/{id}                             a draft file (a posted one is kept)
POST   /api/v1/spins/{id}/proofs                       a draft file on the spin (as today)
POST   /api/v1/spins/{id}/done                         serve: with its draft files, or none when
                                                       the punishment needs none
GET    /api/v1/journal/entries?cursor=                 new: the cards, latest first
```

**Files go first, the post after.** Picking a file starts its upload at once into the day's
check-in as a draft file (the upload engine as today: Uppy, resumable, the global upload manager,
resume by fingerprint). The app keeps the posting button unavailable while any draft file uploads,
and the server refuses too (`uploads_running`). Posting is one transaction: it refuses without a
finished draft file where proof is required (`proof_needed`), deletes the failed ones, creates the
post, sets `post_id` on the finished ones (`proofs.publish(subject, post_id)`), refreshes the
check-in and writes the card. A post without files goes live at once. A double tap finds nothing
left to post and changes nothing.

Nothing goes live on its own: no hook from proofs to posts, no race between uploads finishing. A
card's proofs are the ones with its post's id; deleting a post deletes them. A draft file can be
removed until it is posted; a posted one cannot. The crew sees posted files only: draft files
show on their owner's Today card and nowhere else. Up to 5 draft files at a time.

Only posts count: the day's status and total, streaks, the board, verdicts, the day counts. A
draft file belongs to its day, and midnight ends it (agreed 2026-10-10: no grace after the
deadline): an upload must finish, and its post be made, before the day's deadline. Then
`expire_proofs` deletes the day's draft files, and the next day starts with none.

### Cards

```
JournalEntry(CrewScopedModel)          one card, written once
  kind          CharField(16)          check_in | spin | served | crew_day
  subject_type  FK ContentType         the post (a CheckInEntry), the spin, the crew
  subject_id    UUID
  member        FK Member, null        who did it (none for the crew's day)
  challenge     FK Challenge, null     who may see it (none: the whole crew)
  day           DateField              the crew-local day it sits under
  at            DateTimeField          when it went live: its place, latest first
  facts         JSONField              what the card says, frozen (by kind)
  reactions     GenericRelation        deleting the card deletes its reactions (stage 7: FK)
  unique (kind, subject_type, subject_id, day)   writing twice is harmless
  index  (crew, -at, -id)                        a page is one index range
```

| Kind | Card | Written when | `facts` |
|---|---|---|---|
| `check_in` | "Ana checked in", "+5 km, 8 of 10 today", "Ana added 2 photos" | a check-in post goes live | action (checked in, "+N", added files), amount, total after, target, streak, milestone, proof count |
| `spin` | "Bogdan spun the wheel: 20 burpees" | `doom.draw` | window, need, done, punishment text and number |
| `served` | "Bogdan served it" (with its proofs) | "Done", or the serving goes live | punishment text, proof count |
| `crew_day` | "The whole crew finished the day" | the post that finished it goes live | who was due |

The interface every writer uses: cards are never edited, so there is nothing to move, and
nothing is guessed from the subject:

```python
# apps/journal/services.py
def post(kind: str, subject: Model, *, day: date, facts: dict[str, Any],
         member: Member | None, challenge: Challenge | None,
         at: datetime | None = None) -> JournalEntry:
    """Write the card once, at `at` (default now). Writing it again changes nothing."""

def drop(kind: str, subject: Model, *, day: date) -> None:
    """Delete the card and its reactions, if there is one."""
```

In the API each kind's facts get a typed field of their own (`check_in`, `spin`, `served`,
`crew_day`, one set per entry), as the journal does today, so the app narrows them without casts.

A journal page is one query for the cards, one for their proofs, one for their reactions, and one
aggregate for the day counts of its dividers (check-ins: counting `check_in` cards; proofs: the
sum of their frozen proof counts). About 5 queries, no history loaded, and the cursor never skips
or repeats a card because cards never move.

The journal's store (models, services, selectors) sits below check-ins and the wheel, so they can
write to it; its API stays on top:

```
core <- crews <- challenges <- journal store <- checkins, doom <- journal api
                               proofs          <-'
```

## Sync or async

A card is a few indexed inserts inside a transaction the poster already has (about a
millisecond). Moving it to Celery buys nothing and costs the guarantee.

| | In the poster's transaction (chosen) | Celery, after commit |
|---|---|---|
| A card exists exactly when its post does | Yes | Eventually; a crash between commit and enqueue loses it, so a sweep job is needed |
| Your post on your next refresh | Yes | Maybe not (a race with the worker) |
| Request time | A few small writes | One enqueue (a Redis round trip: about the same) |
| Moving parts | None | A task, retries, idempotency, a sweep, eager-mode tests |
| When it fails | The request fails; nothing half-written | Silent gaps in the journal |

The slow parts are already asynchronous where they must be: the upload (browser to S3) and the
video conversion. Async is also right for what will hang off a card later, Web Push and comment
notifications; for those the card row is the outbox (`post` adds a `transaction.on_commit` task,
idempotent per card, retried by beat). Not built now.

## Stages

Prerequisite: `chore/wheel-cleanup` (the wheel's stage 6: the old `/feed` endpoint and the proof
columns kept for deploys) is rebased and shipped first.

| Stage | Branch | What works at the end | Size |
|---|---|---|---|
| 0. Plan | `docs/journal-plan` | This plan | S |
| 1. Proofs know their post | `refactor/proof-post-id` | Nothing changes for people; every proof records the post that published it | S |
| 2. Post with proof | `feat/posts` | Any check-in or "+N" may carry photos or videos, required where the challenge asks for proof; proofs added later are a post | L |
| 3. Serve with one post | `feat/serve-posts` | "Serve" serves a punishment with its uploaded files (or none when it needs none) | M |
| 4. Write the cards | `feat/journal-cards` | Every post, draw, serving and finished day writes its frozen card; the history too; the app still shows the old journal | L |
| 5. Read the cards | `feat/journal-entries` | Echipa shows one frozen card per post; every card takes its own reactions | L |
| 6. Clean-up | `chore/journal-cleanup` | Old endpoints, derived reads and columns are gone; a release after 5 | M |
| 7. Reactions on cards (optional) | `refactor/reactions-on-cards` | Same screens; reactions are a plain foreign key to the card | S |

Every stage ends with `make check` green (and `make e2e` from stage 2) and is reviewed before it
is committed.

### Stage 0 - Plan

- This plan; glossary rows for Post and Card (the Journal row changes in stage 5).
- `docs/plans/wheel.md`: "proof that decides whether a day is done" leaves "Out of scope" and
  points here.

### Stage 1 - Proofs know their post

The data first, with no change in behaviour, so stage 2 only changes rules.

- Backend: `Proof.post_id` (nullable UUID, indexed; the proofs app does not know what it points
  at). No code reads or writes it yet.
- Migrations (`proofs` 0002, `checkins` 0006, `doom` 0002): each subject's app fills `post_id`
  for its own proofs: a check-in's proofs get
  its first entry's id, a spin's shown proofs the spin's id. Proofs added while this release runs
  are filled by stage 2's migration with the same rule.
- Tests: each fill, run twice on today's models; forward and back on a copy of the dev database.

### Stage 2 - Post with proof (built, 2026-10-10)

The rule change, backend and screens together (the old screens cannot post with proof).

- Backend:
  - `start_proof` on any challenge, before the check-in too (the day's check-in is made with
    `status` `pending` while it has no post); up to 5 draft files at a time.
  - `check_in` posts as above. Whether a post counts follows from what it is: on a "just check
    in" or "held" day the first post is the check-in and later ones add files (a second tap
    already changes nothing, and undo removes only the latest, so the first stays first); on a
    number challenge a post with a number counts (numbers are above zero), one without adds
    files. A post that adds nothing and has no files is a no-op.
  - Undo: my latest post of today, with its files (the check-in goes with its last counting
    post, unless draft files keep it pending).
  - `proofs.publish(subject, post_id)`, `remove_post`, `drafts`; `delete_proof` refuses posted
    files (`proof_posted`; the same-day rule and `ProofKept` go); a draft's upload expires at its
    day's deadline (the 24 h `UPLOAD_GRACE` goes) and `expire_proofs` then deletes it;
    crew-facing reads show posted ones only (`VISIBLE` in
    `records`, `day_sheet`, `feed`, `day_summaries`, `member_progress`); `todays_proofs` (mine)
    shows drafts too, each with `posted`.
  - Pending check-ins: skipped by `records`, day counts and the old journal (verdicts only count
    `done`). One left with nothing (its drafts removed or expired) stays, skipped by every read:
    no beat task until they pile up.
  - New codes: `uploads_running`, `proof_required`, `proof_posted`; `not_checked_in` goes. An old
    app on a challenge that asks for proof gets `proof_required` when it checks in first (the
    update banner follows).
  - Until stage 3, a spin's proofs are posted with the spin as they start (`post_id` = the spin),
    so the shared draft rules leave them alone; in between a spin proof cannot be removed.
- Frontend:
  - Today's card: picking files (any challenge) uploads them as draft tiles you can retry or
    remove; "Check in" is not available while any uploads, and on a challenge that asks for
    proof until one has finished. Without files it posts at once. After the check-in, "Add
    photos or videos", then "Post N photos or videos".
  - The amount sheet: the number and its files; "Add" follows the same rule.
  - When the uploads finish while you are elsewhere, a toast says they are ready to post.
  - Undo deletes your latest post of today. Posted tiles lose "Delete".
- Migrations: `checkins` 0007 (the `pending` status), 0008 and `doom` 0003: `post_id` filled
  again for proofs added while stage 1 ran (every spin proof now gets its spin).
- Docs: `AGENTS.md` (game rules: any post may carry files, none without them where proof is
  required, "Proof never changes whether a day is done" goes; proof upload: draft files),
  glossary (Post, Draft file), `docs/plans/proof-upload.md`, `docs/design-system.md` for any new
  component.
- Tests: posting refused while a file uploads; refused without a finished file where proof is
  required (also a "+N"); files accepted on a challenge that does not ask for proof; a 6th draft
  file refused; failed files deleted at posting; posted files not removable, draft files
  removable; the crew never sees draft files; midnight ends a day's drafts (an upload cannot
  finish after it, a post for yesterday is refused, `expire_proofs` deletes them); only posts
  count (status, total, streak, board, day counts); undo removes the latest post and its files;
  a double tap posts once.
- `make e2e`: check in with a photo (the button waits for the upload); "+N" with its proof; a
  check-in with an optional photo on a challenge that does not ask for proof; add photos later;
  remove a draft file; undo.
- Acceptance: a multi-GB video draft interrupted and resumed on a phone, then posted.

### Stage 3 - Serve with one post (built, 2026-10-10)

- Backend: a spin's files are draft files until it is served (not shown to the crew before);
  `serve` (the `/spins/{id}/done` endpoint, which `mark_done` was) serves in one transaction:
  refused while a file uploads (`proofs.uploaded_drafts`, shared with check-ins), refused without
  a finished file when the punishment needs proof, failed files deleted, the rest published with
  the spin's id, `done_at` set (it now means "served at"; no `served_at` column). No files after
  serving (`spin_served`). The spin's state reads `done_at` only (the "has a shown proof"
  subquery goes); the old journal's served card sits at `done_at`.
- Frontend: the spins page picks files, then "Serve" once they have finished (or "Done" at once
  when the punishment needs no proof); `ProofTiles` loses its stage 2 `drafts` option.
- Migration (`doom` 0004): spins served by a proof the crew could see get that proof's time in
  `done_at`; the files of spins still to serve become draft files. Spins the old release serves
  during the deploy are filled again in stage 4's migration.
- Tests: serving refused while uploading or without a finished file where proof is needed;
  served at once without files where it is not; no files after; the migration.

### Stage 4 - Write the cards

Production fills the cards for a release while everyone still sees the old journal.

- Backend:
  - `apps/journal` store: `JournalEntry`, `post` / `drop`, the `page` selector, a read-only
    admin (filter by day and kind). Contracts: the store imports no kind; check-ins and the wheel
    never import `apps.journal.api`; the wheel's contract stops forbidding `apps.journal` to the
    apps below.
  - Writers, each next to its fact: a check-in post going live writes its card, and the crew's
    day when it finishes the day; deleting a post deletes its card, and the crew's day if the
    day is no longer finished; `draw` writes `spin`; serving writes `served`.
  - `card_facts(post)`: today's `feed_details`, for one post, at the moment it goes live.
  - `journal_backfill`: a management command, idempotent, that writes the cards of the history
    with the same writers (facts as of each post).
- Migration: the table; a data migration that calls `journal_backfill` and fills `done_at` again
  for spins the old release served by a proof during the deploy (as `doom` 0004).
- Tests: one card per live post, never changed by a later one (an earlier "+N" keeps its total);
  deleting a post deletes its card and its reactions; the crew's day appears with the last due
  post, not for weekly challenges, and goes when a deletion un-finishes the day; facts at 23:30
  local and on the 25-hour Sunday; backfill twice is once; `page` latest first, no gaps or
  repeats, hidden challenges absent, the crew's day present, the same number of queries for 1
  card and 30.
- Before stage 5: compare the cards with the old journal in production, in the admin (cards per
  day and kind against the old journal's).

### Stage 5 - Read the cards

- Backend:
  - `GET /api/v1/journal/entries` as above; the old `GET /api/v1/journal` stays a release.
  - Reactions on cards: the journal registers the `entry` target; a data migration moves each
    reaction to its card. The `check_in` and `spin` targets stay a release.
  - The migration runs `journal_backfill` again, for posts the old release made during the
    deploy.
- Frontend:
  - The journal reads entries; `journal.ts` keeps only the days (`entry.day`): no grouping, no
    crew card of its own, no `plain`.
  - `CrewFeed` draws each card from its facts; `SpinFeedCard` from the spin's facts; every card
    has reactions on target `entry`, patched by entry id. `FeedCard` loses `week`.
  - The new-proofs badge (`freshCounts`, from `checkInsOf`) counts the proofs on cards.
- Docs: `backend.md` (the journal's layers), `api-conventions.md`, glossary (Journal: stored,
  "Derived, nothing stored" goes), `docs/plans/reactions.md` (targets).
- Tests: a reaction on the served card is not on the drawn card; the crew's day takes one; each
  moved reaction is on the right card; the badge counts proofs on cards.
- `make e2e`: react to a check-in card, a served card and the crew's day.

### Stage 6 - Clean-up

Deployed a release after stage 5, because that release still serves what this removes.

- Endpoints: `GET /api/v1/journal` (derived).
- Code: `checkins.feed`, `feed_details`, `FeedDetail`, `day_summaries`, `DaySummary`,
  `reactable_check_in`, `FeedItemOut`; `doom.journal`,
  `doom.served`, `_visible`, `shown_proofs`, `reactable_spin`, `journal_day`, `spin_items`,
  `SpinItemOut` (with the unused `punishment_count`);
  `JournalEntryOut` and `JournalPageOut` of the old journal; the `check_in` and `spin` reaction
  targets and the `reactions` relations on `CheckIn` and `Spin`, after moving the reactions made
  on them since stage 5. Frontend: `checkInsOf`, `FeedItem` and the old journal types.
- Migrations: the stage 4 and 5 data migrations' bodies become no-ops (an old migration must
  not run today's code; `journal_backfill` stays as the repair tool).
- `make schema`; docs lose every mention of the removed parts.

### Stage 7 - Reactions on cards (optional)

- `Reaction.entry`, a foreign key to the card (cascade), filled from the generic key; then
  `targets.py`, the `ContentType` lookups and the generic columns go (columns in two releases).
- The URL and the `<Reactions>` component stay (`target` is always `entry`); comments (the next
  plan) use the same foreign key.

## Edge cases

| Case | Behaviour |
|---|---|
| A file fails or is stuck | Retry it or remove it; the button waits only for the files still there |
| Every file failed, proof required | "Check in" stays unavailable until a file finishes; remove them and pick again |
| Every file failed, proof optional | Remove them (or post: failed files are dropped and the check-in has none) |
| The app is closed during an upload | Pick the same file again: the generic resume finds it; the draft waits |
| Uploads finish while you are elsewhere | A toast says they are ready; Today keeps "Check in" waiting for your tap |
| Picked at 23:50, not posted by midnight | The day is over: the upload stops, the draft goes, nothing counts; pick again for the new day |
| Draft files never posted | They expire at their day's deadline; nothing counts |
| Checked in on another device while draft files wait | Posting them adds them as a post of their own (it counts nothing more) |
| A double tap on "Check in" | The second finds nothing to post |
| A 6th draft file | Refused: up to 5 at a time |
| Deleting an earlier post of today | Refused: only the latest (the later cards' totals stay true) |
| Deleting a post that finished the crew's day | The crew's card goes too (and its reactions) |
| A day with only weekly or monthly challenges | No crew's day card |
| Leaving a challenge with draft files | Today still counts: they can be posted today, or expire |
| A deleted challenge | Its cards are hidden with it (`visible` hides deleted challenges) |
| A video whose conversion fails | Shown as today: the original plays where the browser can |
| Deleting a post that has reactions | Its card and the reactions go |
| A "held" challenge that asks for proof | Same rule: a photo or video with each post |

## Removal checklist

| Item | Where | Stage |
|---|---|---|
| The same-day rule for deleting a proof; "Delete" on posted tiles | backend, frontend | 2 |
| "This challenge takes no proof"; the per-subject limit of 5 (now 5 draft files at a time) | backend | 2 |
| The "add a photo" nudge after a plain check-in | frontend | 2 |
| `has_shown` for a spin's state | backend | 3 |
| Grouping, `plain` and the crew card in `journal.ts`; `FeedCard.week` | frontend | 5 |
| `GET /api/v1/journal` (derived) | backend | 6 |
| `feed`, `feed_details`, `day_summaries`, `reactable_*`, `journal_day`, `spin_items`, `punishment_count`, old serializers | backend | 6 |
| `checkInsOf`, `FeedItem`, old journal types | frontend | 6 |
| `check_in` and `spin` reaction targets, `reactions` relations on `CheckIn` and `Spin` | backend | 6 |
| `reactions/targets.py`, the generic key on `Reaction` | backend | 7 |

## Risks

| Risk | Answer |
|---|---|
| Filling `post_id` goes wrong | Stage 1 fills one column and nothing reads it yet; run forward and back on a copy of the dev database; stragglers filled again in stage 2. |
| A day counted wrong while an upload runs | Only posts count; draft files count nothing; tests at midnight and on the 25-hour day. |
| A long video started late is lost | Agreed: the day ends at midnight; the button shows the upload's progress, and a big video asks before it starts on a phone. |
| Members think an upload is a check-in | The button stays visible but waiting, with the upload's progress; a toast when ready; Today keeps the draft files until posted. |
| Draft files seen before posting | Crew-facing reads show posted files only; a test for each. |
| Cards that do not match what happened | Stage 4 writes them for a release before anyone reads them; compare in the admin; `journal_backfill` repairs. |
| Old app during a deploy | Old endpoints stay a release; the new rule answers `proof_needed`; the update banner. |
| Large uploads | Uploads run as today, one request per file, same endpoints; a multi-GB draft interrupted, resumed and posted in stage 2. |
| `facts` shape drifting | Typed per kind in the schema; only additive changes; old cards keep their shape. |

## Comments (the next plan, sketched to check that the model fits)

`Comment(entry FK CASCADE, member, text up to 500, created_at)`; `GET` / `POST
/api/v1/journal/entries/{id}/comments`, `DELETE /api/v1/comments/{id}` (your own). The page gets
`comment_count` from one subquery. Deleting a post deletes its card's comments too. Nothing in
this plan changes for it.

## Out of scope

Comments (the next plan), Web Push (after v1), editing a posted card, posting a draft
automatically when its uploads finish.
