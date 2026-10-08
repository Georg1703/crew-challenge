# Plan: proposing and choosing challenges (monthly rounds)

Status: built. Periods (months only, the round model) are superseded by
`docs/plans/periods.md`: a proposal says how long it runs and an admin picks the start.

## Goal

Anyone in a crew can propose a challenge for next month and everyone can vote. A crew admin
looks at the proposals and the votes and chooses which one becomes next month's challenge; it
starts on the 1st. The whole crew takes part by default; anyone can opt out before it starts.

v1 ships **monthly rounds only**, but nothing in the model may assume "a month": rounds and
challenges carry explicit start and end dates and a period kind, so weekly and custom periods
can be added later without a data migration.

## Decisions (agreed)

| Topic | Decision |
|---|---|
| Who proposes | Any member of the crew. |
| Who sees proposals | Only that crew. Every challenge shows who proposed it and when. |
| How the next challenge is chosen | Monthly round: members propose and vote; an admin chooses the challenge for next month (votes guide, they do not decide). It starts on the 1st. |
| Proof | Chosen by the creator: none, photo, video, or photo or video; required or optional. |
| Measurement | Versatile: just check in, a number with a unit, or "held it" (abstain). See "Challenge shape". |
| Participants | Whole crew by default; each member can opt out. |
| Editing | The creator can edit a proposal while the round is open. Every edit resets its votes. Once a challenge is chosen it cannot be edited. |
| Deleting | Soft delete only. Default manager returns only rows that are not deleted. |
| Rotation | Removed: `Member.rotation_position`, the reorder endpoint and every "proposer" rule. |

## Decisions with a proposed default (confirm or change)

1. **No deadline in v1.** The round for next month stays open (propose, edit, vote) until an
   admin chooses. Choosing closes the round. The now unused `Crew.proposal_deadline_day` and
   `Crew.reveal_time` are removed with the rotation.
2. **One vote per member per round**, changeable while the round is open. You may vote for your
   own proposal.
3. **Votes are visible to everyone:** each proposal shows its count and who voted, so the admin's
   choice is easy to follow.
4. **Admins can change their choice until the period starts** (for example, the chosen challenge
   turns out impossible). From the 1st it is locked.
5. **Chosen late:** if no admin chooses before the 1st, the month has no challenge yet; when an
   admin chooses during the month, it starts the next day and ends with the month. Today shows
   admins "Choose next month's challenge" from the 25th (`CHOOSE_REMINDER_DAY`, a constant).
6. **Opting out** is allowed until the challenge starts. After the start a member can "leave":
   from the next day they no longer count (their past check-ins stay). Members who join the crew
   during a running challenge are added from their join day.
7. **Who can delete a proposal:** its creator, or a crew admin (for moderation). Both soft.
8. **Proposals not chosen** stay visible in the round's history with state `not_chosen`, and have
   a "propose again" action that copies them into the next open round.
9. **Later, automatic selection** (most votes wins at a deadline) plugs in as a second value of
   `Round.selection` (`admin` now, `votes` later) without changing the other rules.

## Challenge shape (four independent choices)

| Choice | Values (v1) | Stored as |
|---|---|---|
| What you record per check-in | `check` (just done), `quantity` (a number + unit), `abstain` ("held it") | `measure`, `unit` |
| How often | `daily`, `weekdays` (chosen days), `times_per_week`, `times_per_period`, `once` | `frequency`, `weekdays` (bitmask), `times` |
| Target (quantity only) | per check-in, per week, per period, total for the challenge | `target_scope`, `target_value` |
| Proof | `none`, `photo`, `video`, `photo_or_video`; required or optional (now yes or no, see `docs/plans/wheel.md`) | `proof_kind`, `proof_required` |

Plus `title` (60), `rules` (500, optional), `icon` (a key from a fixed list in `Icon`).
Validation lives in `services.py` (for example `unit` and `target_*` only with `quantity`,
`times` only with `times_per_*`, `weekdays` only with `weekdays`). "Period" means the challenge's
own start..end, so "times_per_period" keeps working when periods are weeks or custom ranges.

## Data model

### Generic soft delete (`apps/core`)

```python
class SoftDeleteQuerySet(QuerySet):
    def alive(self): ...            # deleted_at IS NULL
    def dead(self): ...
    def delete(self): ...           # bulk soft delete (sets deleted_at), never a hard delete

class SoftDeleteModel(TimeStampedModel):   # abstract
    deleted_at = DateTimeField(null=True, blank=True, db_index=True)
    objects = SoftDeleteManager()          # alive rows only (the default manager)
    all_objects = SoftDeleteQuerySet.as_manager()  # every row, for admin, history, restore

    class Meta:
        abstract = True
        base_manager_name = "all_objects"  # FK access to a deleted row still works

    def delete(self, using=None, keep_parents=False): ...  # soft
    def hard_delete(self): ...                             # admin and tests only
    def restore(self): ...
```

- `deleted_at` comes from `clock.now()`.
- Unique constraints on soft-deleted models use `condition=Q(deleted_at__isnull=True)`.
- `apps/crews` adds `CrewScopedSoftDeleteModel` whose queryset combines `for_crew()` with
  `alive()` (core must not import crews; import-linter enforces it).
- Django admin lists `all_objects` and shows a "deleted" filter.
- Tests: default manager hides deleted rows; `all_objects` sees them; related access still works;
  queryset `.delete()` is soft; restore works.

### `apps/challenges` (new app, same layout as every app)

```
Round (CrewScopedModel)
  period_kind      month | week | custom        # v1 creates only "month"
  period_start     date (crew local)            # first day of the challenge period
  period_end       date (crew local)
  selection        admin                         # later also: votes
  state            open | closed                 # closed once a challenge is chosen
  chosen           FK Challenge, null
  chosen_by        FK Member, null, SET_NULL
  chosen_at        datetime UTC, null
  unique (crew, period_kind, period_start)

Challenge (CrewScopedSoftDeleteModel)
  round            FK Round
  created_by       FK Member, SET_NULL           # "proposed by Ana, 4 Oct"
  title, rules, icon
  measure, unit, frequency, weekdays, times, target_scope, target_value
  proof_kind, proof_required
  state            proposed | chosen | not_chosen
  start_date, end_date   # set when chosen (the round's period, or from the next day if chosen
                         # late); null while proposed
  revision         int, +1 on every edit (votes reset)

Vote (CrewScopedModel)
  round            FK Round
  member           FK Member
  challenge        FK Challenge
  unique (round, member)

Participation (CrewScopedModel)
  challenge        FK Challenge
  member           FK Member
  joined_on        date (crew local)
  left_on          date, null                    # opt out before start = row deleted; leave = left_on
  unique (challenge, member)
```

Phase of a chosen challenge is derived, never stored: `upcoming` before `start_date`, `active`
between `start_date` and `end_date` (crew local, via `apps/core/clock.py`), `finished` after.

## Rules (all in `services.py`)

- `propose_challenge(by, **shape)` - into the crew's open round; validates the shape.
- `edit_proposal(by, challenge, **shape)` - creator only, round open; `revision += 1`; deletes
  the challenge's votes (those voters can vote again).
- `withdraw_proposal(by, challenge)` - creator or admin, round open; soft delete; deletes votes.
- `cast_vote(by, challenge)` / `clear_vote(by, round)` - round open, challenge in that round.
- `choose_challenge(by, challenge)` - admin only; closes the round, marks the chosen challenge
  `chosen` (dates from the round, or from tomorrow if the period already started) and the others
  `not_chosen`, creates `Participation` rows for every member, opens the next round. Calling it
  again with the same challenge changes nothing (idempotent).
- `change_choice(by, challenge)` - admin only, before the period starts: swaps the chosen
  challenge (participations follow; opt-outs of the old one are dropped).
- `ensure_open_round(crew)` - creates the next round if missing (called on first read and after
  close), so a new crew always has one.
- `opt_out(by, challenge)` / `opt_in(...)` before start; `leave(by, challenge)` after start.
- `repropose(by, challenge)` - copies a `not_chosen` challenge into the open round.
- Locks: the round row is locked (`select_for_update`) in choose, vote, edit and withdraw, so a
  vote can never land on an edited proposal or a closed round.
- No Celery task is needed for choosing; only reads compute phases from the crew's local date.

## API (`/api/v1`, crew from the session like every crew endpoint)

| Method and path | Who | What |
|---|---|---|
| `GET /rounds/current` | member | The open round: period, proposals (shape, creator, created_at, vote count, voters), `my_vote` |
| `GET /rounds/{id}` | member | A closed round with the chosen challenge, who chose it and the counts |
| `PUT /rounds/{id}/choice` | admin | `{challenge_id}`: choose (or change before the period starts) |
| `POST /challenges` | member | Propose into the open round |
| `PATCH /challenges/{id}` | creator | Edit while open; resets votes |
| `DELETE /challenges/{id}` | creator, admin | Soft delete while open |
| `POST /challenges/{id}/repropose` | member | Copy a not-chosen one into the open round |
| `PUT /rounds/{id}/vote` | member | `{challenge_id}`; replaces your vote |
| `DELETE /rounds/{id}/vote` | member | Clear your vote |
| `GET /challenges?phase=active,upcoming,finished` | member | Chosen challenges with participants |
| `GET /challenges/{id}` | member | One challenge (any state) |
| `PUT /challenges/{id}/participation` / `DELETE` | member | Opt in or out (before start), leave (after) |

Error codes (mapped in `ro.json` / `en.json`): `round_closed`, `not_your_proposal`,
`challenge_started`, `invalid_challenge_shape`, `challenge_not_found`, `not_crew_admin`.

## Screens (design canvas flow 2, adjusted)

- **Today:** while a round is open, a card "Propose next month's challenge" (or "Vote for next
  month" when proposals exist); for admins from the 25th, "Choose next month's challenge";
  once chosen, the chosen challenge and its start date.
- **Propose (wizard):** 1 What (title, icon, quick ideas) -> 2 How often -> 3 What you record
  (and target) -> 4 Proof -> 5 Review. The period step is gone in v1 (always next month); the
  model keeps dates for later.
- **Proposals and vote:** list of proposals for next month with creator, date, vote count and
  voters, one vote button each, "you voted for ..." state; edit or withdraw for your own.
  Admins also get "Choose this one" on each proposal (confirmed in a sheet).
- **Chosen:** the chosen challenge, "chosen by Ana", the counts, "starts on 1 November".
- **Challenges:** Active, Upcoming, Finished (and the round history with not-chosen proposals).
- **Challenge detail:** shape in plain words, proposed by and when, participants, opt out or leave.

New canvas boards are needed for the vote list, the admin choice sheet, the chosen state and the
opt-out sheet before building.

## Removing the rotation

- `Member.rotation_position` (field, constraint, migration), `reorder_rotation`,
  `next_in_rotation`, `PATCH /crew/rotation`, `RotationIn`, rotation tests and factory fields.
- Members are listed by join date (`created_at`) instead.
- `Crew.proposal_deadline_day`, `Crew.reveal_time` and their check constraint (no longer used).
- `AGENTS.md` game rules, `docs/glossary.md` (Rotation, Proposer), `docs/architecture/*` are
  rewritten to the round rules.
- Frontend: `rotation_position` disappears from the client types; fixtures updated.

## Phases (one branch and PR each)

| Phase | Branch | Done when |
|---|---|---|
| 0 | `refactor/remove-rotation` | Rotation gone everywhere, docs updated, `make check` green |
| 1 | `feat/soft-delete` | `SoftDeleteModel` in core with tests and a recipe in `docs/recipes/` |
| 2 | `feat/challenges-api` | Models, services, API, contract; service tests cover every rule, including choosing late, changing the choice and DST months |
| 3 | design | Canvas boards for vote list, admin choice, chosen state, opt out |
| 4 | `feat/challenges-screens` | Wizard, vote list, reveal, lists, detail; Vitest for each state |
| 5 | `test/challenges-e2e` | Playwright: propose, edit resets votes, vote, admin chooses, members see the choice, opt out; "active on the 1st" is covered by backend tests with time travel |

## Test cases that must exist

- Only admins can choose or change the choice; changing is refused from the period's first day
  in the crew time zone (also in DST months and for a crew in another time zone).
- Choosing twice with the same challenge creates one set of participations and one next round.
- Choosing late (during the month) starts the challenge the next day and ends it with the month.
- Edit resets only that challenge's votes; voters can vote again.
- Vote on a withdrawn, edited-away or other-round challenge is rejected.
- Non-member of the crew gets 404 on every challenge and round id (no cross-crew reads).
- Soft-deleted challenges never appear in lists, votes or counts.
- Opt out before start removes participation; leave after start keeps past check-ins.

## Out of scope for this plan

Check-ins, proof upload, streaks (next plans). Weekly and custom rounds (the model allows them;
no UI). Automatic selection by votes (`Round.selection = votes`). Push notifications (after v1).
