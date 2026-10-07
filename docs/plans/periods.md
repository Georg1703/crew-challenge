# Plan: periods, windows and requirements

Status: stages 1-3 merged into `main` and deployed (2026-10-07); stage 0 on
`chore/challenges-dead-code`; stages 4 and 5 to do. One branch and one pull request per stage. Explainer with diagrams and worked examples (private, the owner's):
https://claude.ai/artifact/1K7fg8iWqb2z6Zb1BwrQZx

Priorities, in order: judging is exactly right (it will decide punishments), the crew always sees
what is asked of them, the code ends smaller than it starts, with no dead code left behind.

## Goal

Every challenge is judged the same way, whatever its rhythm. A challenge's rule has three parts:

- **Period**: when it runs (start and end date).
- **Window**: the unit that is judged (a day, a Monday-Sunday week, a month, the whole period).
- **Requirement**: what each window needs (a number of check-ins or a total amount, optionally
  only on chosen weekdays, optionally with a minimum for a day to count).

One pure function judges each window: `met`, `failed` (short by N), `open` or `future`. Missed
days, streaks, progress, today's ring and, later, the Wheel of Doom's spins all come from it.

Why now: the Wheel of Doom needs "failed" for every kind of challenge ("3 times a week" has no
missed days today), and the current code branches on `frequency` in about six functions and
repeats the "due day" check in four places, so every new rhythm touches all of them.

## Words (glossary changes)

| Term | Code name | Meaning |
|---|---|---|
| Period | `period_start`, `end_date`, `period_kind`, `period_length` | When a challenge runs. Its length is part of the proposal (`period_kind` month / week / day, `period_length` how many); an admin picks the start. |
| Window | `Window` | A stretch of days judged as one unit: a day, a Monday-Sunday week, a calendar month or the whole period. |
| Requirement | `need_kind`, `need_value`, `on_days`, `day_min` | What each window needs: N check-ins (`count`) or a total (`amount`); `on_days` limits which weekdays count; `day_min` is the least amount for a day to count. |
| Need | `Window.need` | What one window asks for, after scaling. |
| Short window | `Window.full_need` > `Window.need` | A window cut by the period's edges, a late start or leaving; it asks for less, in proportion to the days that count. |
| Verdict | `days.Verdict` | `met`, `failed` (with `short`), `open` (today is in it), `future`. |
| Due day | `days.is_due` | Kept, redefined: a day that counts in a challenge judged per day (daily or chosen days). |
| Missed day | - | Kept: a failed day window. |
| Goal | `goal_label`, `goal_target` | Removed: these fields never existed (stage 0). |

## Decisions (agreed 2026-10-07)

| Topic | Decision |
|---|---|
| Model | Period + window + requirement, judged by one pure function; nothing judged is stored. |
| Spins per failed window | One per missing check-in (1 of 3 -> 2 spins); one for a missed amount. Wheel of Doom plan. |
| Week start | Monday, like every week strip in the app. |
| Short windows | Need x (days that count / full days), rounded half up for counts, one decimal for amounts. A need of 0 is not judged. |
| Early failure | Not judged early; a window is judged after its last day. The card may say it can't be met. |
| First new options | Week and day-range periods, and the month window. |
| Repeating periods | Later. |
| Production | One running monthly challenge with a daily check-in; it maps one to one, no compatibility code. |
| Showing short windows | Always show the scaled need and say why it is lower: Today card, challenge page, schedule sheet, wheel card. |

## Decisions taken while building (all built as first proposed)

1. **The creator sets the length, an admin picks the start.** The requirement depends on the
   length ("8 times" in a week or in a month), so it is part of what the crew votes on.
   Moving a scheduled challenge changes only its start.
2. **Lengths:** 1-12 months, 1-52 weeks, 1-365 days. Starts up to 12 months ahead
   (`MONTHS_AHEAD`); the sheet offers the next 3 months, the next 8 Mondays, or any date.
3. **Days that don't count can't be checked in**, as today for chosen-day challenges
   (`NotDueToday`).
4. **The board stays a month calendar of days.** A failed week shows in the challenge page's list
   of windows and on the wheel card, not as board cells.
5. **Not offered yet:** "every N days" (one generator plus tests, added when a real challenge asks
   for it) and weekly quotas on chosen days (free in the engine through `on_days`, kept out of the
   wizard).
6. **Daily check-in with a weekly or period total** (if any exists): the migration maps it to the
   total, judged per week or period. Expected: none in production (checked before stage 2).
7. **Feed milestones ("7 days in a row") stay for challenges judged per day**, as today.

## The model (end state)

```
Challenge
  period_kind      month | week | day       the length's unit (creator)
  period_length    1..12 / 1..52 / 1..365   how many (creator)
  period_start     date, null while proposed  first day of the period (admin)
  end_date         date, null while proposed  last day (computed)
  start_date       date, null while proposed  first day that counts: period_start, or
                                            tomorrow when scheduled late
  window           day | week | month | period
  on_days          weekday mask, 0 = every day   (today's `weekdays` column, renamed)
  need_kind        count | amount
  need_value       decimal                  N check-ins, or the total
  day_min          decimal, null            least amount for a day to count
  measure, unit    unchanged
```

Defaults (so `tests/factories` and seeds stay short): window day, need count 1, period month 1.

Constraints: a proposal has `period_kind` and `period_length`, a chosen challenge also its three
dates (replaces `challenge_period_matches_state`, which today requires an empty `period_kind`);
`need_kind = amount` and `day_min` only with `measure = quantity`; `need_value >= 1` for counts;
the window fits the period (a month window needs a period counted in months, a week window at
least 7 days); a count over the whole period is at most the days that count in it.

Mapping used by the data migration:

| Today | window | on_days | need_kind, need_value | day_min |
|---|---|---|---|---|
| `daily` | day | 0 | count, 1 | - |
| `weekdays` + mask | day | mask | count, 1 | - |
| `times_per_week`, N | week | 0 | count, N | - |
| `times_per_period`, N | period | 0 | count, N | - |
| `once` | period | 0 | count, 1 | - |
| `target_scope = per_check_in`, T | (from frequency) | (from frequency) | (from frequency) | T |
| `target_scope = per_week`, T | week | 0 | amount, T | - |
| `target_scope = per_period`, T | period | 0 | amount, T | - |

Every existing row gets `period_kind = month`, `period_length = 1` (all were proposed for, or run
in, a month).

## The engine

Two pure modules, no database and no clock (callers pass `clock.crew_today(crew)`); imports keep
their direction (`checkins` -> `challenges`):

```python
# apps/challenges/windows.py - which windows exist and what each one needs
@dataclass(frozen=True)
class Window:
    first: date
    last: date
    need: Decimal        # scaled
    full_need: Decimal   # before scaling

def counts_on(challenge, day) -> bool                            # on_days
def windows(challenge, first: date, last: date) -> list[Window]  # the member's days
def window_at(challenge, first, last, day) -> Window | None

# apps/checkins/days.py - judged against check-ins (rewritten on top of windows)
def is_fixed(challenge) -> bool      # judged day by day (the window is a day)
def is_due(challenge, day) -> bool   # is_fixed and counts_on(day): one line, one place
def judge(challenge, window, record, today) -> Verdict
def state(...)          # day states, same values as today
def streak(...)         # met windows in a row; open and future skipped
def longest_streak(...)
def progress(...)       # the current window
def settled_today(...)
```

`windows()` is the only code that knows window kinds. `is_due` replaces the four copies of
"`is_fixed` and `is_due`" (check-in service, `day_summaries`, `member_progress`, the history seed).
The check-in service uses `counts_on` (a weekly challenge can be checked in any day that counts).
Day states keep their meaning: a past day in a day window without a counting check-in is `missed`;
days in other windows are never `missed` themselves (their window fails instead), as today.

Calendar helpers live in one place, `apps/challenges/periods.py`: `month_of`, `add_months`,
`week_of` (moved from `days.py` in stage 1, since the window module needs it and may not import
`checkins`) and, in stage 3, `period_end(kind, start, length)`.

## Changes people will notice

1. **Short weeks ask for proportionally less.** "3 times a week" in a 4-day first week asks for 2.
   Today it asks for min(3, 4) = 3.
2. **A whole-period count scheduled late scales too.** "8 times in October" chosen on the 14th
   asks for 4 from the 15th. Today it asks for 8 in 17 days.
3. **Weekly and period totals are judged** (today they only show progress).
4. **Proposals say how long they run**, and admins can schedule weeks and day ranges, not only
   months.
5. **Short windows are explained** wherever the need shows.
6. **The wizard asks "What do you record?" before "How often?"**, and for numbers "How often?"
   offers weekly and whole-period totals; the per-check-in minimum is an optional field there.
7. **Progress shows what was done, not capped:** a "once" challenge checked in on two days shows
   "2 of 1" (today it caps at 1; weekly counts were never capped).

The production challenge (daily, monthly) is untouched by 1-3; stage 1's golden tests prove it.

## Stages

Each stage is one pull request, ends with `make check` green and is reviewed before the next.
Stages 0-2 change nothing for the production challenge; features come after. Every stage lists
what it removes; the checklist at the end must be empty when stage 5 merges.

| Stage | Branch | What works at the end | Size |
|---|---|---|---|
| 0. Clean-up | `chore/challenges-dead-code` | Dead code and stale docs found while planning are gone | S |
| 1. One engine | `refactor/window-engine` | `days.py` runs on windows built from today's fields; short weeks scale; API unchanged | M |
| 2. Rule fields | `refactor/challenge-rule-fields` | The rule fields and their data migration; old fields leave the model (the database drops them in stage 3); the wizard asks for totals in "How often?" | L |
| 3. Weeks and day ranges | `feat/period-length` | Proposals say how long; admins schedule months, weeks or day ranges; old columns dropped | M |
| 4. Month windows | `feat/month-window` | "N times a month" and "a total per month" in periods of whole months | S |
| 5. Showing windows | `feat/window-hints` | Short-window tag on Today, the list of windows on the challenge page, notes in the schedule and leave sheets | M |

The Wheel of Doom gets its own plan; it can start after stage 2 (it needs `judge()` and the final
fields) and run alongside stages 3-5.

### Stage 0 - Clean-up (no behavior change) - done

Found while planning; each was unused or described something that doesn't exist.

- Backend: `periods.next_month_of` (never called); the second `ChallengeNotFound` in
  `apps/checkins/services.py` (same code and message as the one in `apps/challenges/services.py`;
  checkins imports it instead).
- Frontend: i18n keys `challenges.until`, `challenges.open`,
  `challenges.facts.{period,proposed,chosen,votes}` (in both files); the `DaySheetRow` type in
  `features/checkins/api.ts`; the `month` argument of `useMemberProgress` (never passed).
- Docs: the glossary's Goal row and the `goal_target` example in
  `docs/architecture/api-conventions.md` (no such fields); that page's error table, now listing the
  codes the services raise (several were missing, and `not_invited` no longer exists); the copy of
  the import-linter contracts in `docs/architecture/backend.md` (4 of 9, with apps that don't
  exist), replaced by a summary that points to `backend/pyproject.toml`.

### Stage 1 - One engine (backend only, API unchanged)

- First, **golden tests**: for daily and chosen-day challenges, record what today's `state`,
  `streak` and `longest_streak` return on a set of histories (gaps, partial amounts, today done
  and not done, leaving), as plain expected values in a parametrized test. They stay after the
  rewrite as regression tests; no copy of the old code is kept.
- `apps/challenges/windows.py`: `Window`, `counts_on`, `windows`, `window_at` (day, week and period
  windows), reading today's fields through one small `rule_of(challenge)`.
- `apps/checkins/days.py`: `is_fixed` and `is_due` (one line each over windows), `judge`, and
  `state`, `streak`, `longest_streak`, `progress`, `settled_today` rewritten over windows.
  `is_fixed` stays: feed milestones, day states and the seed ask "judged day by day?".
- Callers: `check_in` uses `counts_on`; `day_summaries`, `member_progress` and the history seed
  use `is_due` alone; `week_of` moves to `periods.py`.
- Removed: `days.FIXED`, `days.week_quota`, `days.done_between`, `days.week_of`, the frequency
  branches in `days.py`. The weekly tests are rewritten for scaled weeks (not kept beside them).
- Found while capturing the golden values: a check-in on a day that isn't due (refused by the
  service, so it never happens) added to `streak` but not to `longest_streak`. The golden tests
  use only check-ins on due days.
- New tests: `windows` for every kind, short windows at both edges, leaving mid-window, rounding
  (0.5 up; one decimal for amounts), need 0 not judged, weeks across months and years, February,
  `on_days`; `judge` (met early, open today, failed the day after, amounts); streaks with an open
  window; midnight and DST in `Europe/Chisinau` with time-machine (23:59 / 00:01, and Sunday
  October 25, 2026, when clocks go back).
- Docs: glossary (Window, Need, Short window, Verdict, Due day, Streak), the AGENTS.md game rule
  on missed days, `docs/architecture/backend.md` (the engine).
- Done when: the golden tests pass; `Frequency` appears only in `rule_of`, the model and the
  serializers.

### Stage 2 - Rule fields (backend and frontend) - done

Two things found while building it changed the plan:

- **Old columns leave in two releases** (`docs/recipes/new-migration.md`: migrations must work with
  the previous release while it still serves). `0007_challenge_rules` adds `window`, `on_days`,
  `need_kind`, `need_value`, `day_min` with their constraints and makes the old columns nullable;
  `0008_fill_challenge_rules` fills the new fields (reversible) and removes the old ones from the
  model only. The database drops them in stage 3. So the model has no dead fields.
- **The period fields move to stage 3.** Proposals carrying `period_kind` now would break the
  existing constraint while the old code still writes proposals; stage 3 migrates the table
  anyway. `ScheduleIn` keeps `period_kind` and `PeriodKindNotAvailable` stays until then.

What was done:

- Engine: `rule_of` is gone; `windows.py` and `days.py` read the fields.
- Services: shape validation on the new fields (a day window needs one check-in; up to 7 a week and
  31 in the period; totals only with numbers and only per week or period; `day_min` only for
  counted numbers; chosen days only per day). `TIMES_MAX` and `_days_needed` are gone.
  `TooFewDays` stays, but checks the whole period (30 times in February): a late start now asks
  for less instead of being refused.
- API: `ChallengeIn` / `ChallengeOut` and the Today card carry `window`, `on_days`, `need_kind`,
  `need_value`, `day_min`; `window`, `need_kind` and `need_value` are required, so a cached old
  app gets an error instead of a silently different challenge. Help texts reworded. Contract and
  client regenerated.
- Wizard (owner's choice, 2026-10-07): "What do you record?" comes before "How often?"; for numbers,
  "How often?" also offers "A total each week" and "A total for the month"; "Each check-in at
  least" is an optional field there for counted numbers. One helper parses typed numbers.
  `describe.ts`: `describeRule` and `describeDayMin`. i18n keys renamed to the new words
  (`options.often`, `fields.often`, `fields.onDays`, `errors.onDays`, `errors.number`); the
  target keys are gone.
- Seeds: both on the new fields; `seed_demo_history` picks weekly days from `windows()` and has a
  smoke test.
- Tests: the migration's mapping (every old combination, and back); the real migration was run
  forward and back on the dev database (9 challenges, old columns identical after going back).
- Not done: a pair of weekday-mask helpers. Only one conversion each way is left (the shape check,
  the challenge view), so helpers would not remove anything.
- Production (the owner, before deploying): list the shapes in use, read-only:

  ```python
  from apps.challenges.models import Challenge
  Challenge.all_objects.values("state", "frequency", "measure", "target_scope").distinct()
  ```

  Expected: the running challenge (`daily`) and pool proposals. Before and after the deploy, note
  the running challenge's board and streaks; they must match.

### Stage 3 - Weeks and day ranges - done

- Migrations: `0009_period_length` adds `period_length`, makes `period_kind` month / week / day
  (CUSTOM goes) and rewrites the period constraint without asking proposals for an empty kind (the
  previous release still writes one during the deploy); `0010_fill_period_lengths` gives every
  row a kind and length (proposals and months: 1 month; the seed's custom ranges: their days);
  `0011_drop_old_rule_columns` drops `frequency`, `weekdays`, `times`, `target_scope`,
  `target_value` from the database. All three go back too: run forward and back to 0006 on the
  dev database, the old columns came back identical.
- Services: proposals carry `period_kind` and `period_length` (1-12 months, 1-52 weeks, 1-365
  days); a weekly rule needs at least 7 days; a count over the period is at most its longest
  possible days. `schedule_challenge(by, challenge_id, period_start)`: months on the 1st, weeks on a
  Monday, days from tomorrow; a month or week under way starts tomorrow; `periods.period_end`
  computes the end; moving keeps the length; `unschedule_challenge` keeps the kind and length.
  `PeriodKindNotAvailable` is gone; `PeriodTooFar` names `MONTHS_AHEAD`.
- API: `ChallengeIn` takes `period_kind`, `period_length` (default month, 1: what a cached old
  app means); `ChallengeOut` returns them; `ScheduleIn` is `{period_start}`.
- Wizard: "How long does it run?" (`Segmented` and `Stepper`) at the top of "How often?"; weekly
  choices only when the period has 7 days or more; options and sentences name the period ("8 times
  in 4 weeks"); the review shows the length; proposals show it as a pill and in list lines.
- Schedule sheet: the month or week under way (from tomorrow) and the next 3 months or 8 Mondays,
  or a date field for a number of days, with the end shown. The challenge page shows a period as
  dates unless it is one whole month. The "next month has no challenge" reminder counts monthly
  challenges only.
- Duplicated date code: backend `periods.dates` and `periods.month_of` replace four copies;
  frontend `shared/lib/dates.ts` replaces the copies in `ChallengeBoard`, `CrewRoute`, `CrewFeed`,
  `CheckInCard`, `format.ts` and three day-of-month reads. `months.ts` became
  `features/challenges/periods.ts` (only the start options; the date math moved to `dates.ts`).
- Text: schedule texts, period errors and descriptions no longer say "month"; dead keys gone.
- e2e: the wizard helper follows the new step order (stage 2 broke it); a new flow proposes
  "3 times a week for 4 weeks" and schedules it on a Monday. All e2e tests pass, after three fixes
  to run them locally: pnpm started from `frontend/` (corepack), one test at a time (several
  specs check in as the same person), `seed_demo` bringing back removed demo logins. Checking in
  is not part of it (the period starts tomorrow at the earliest).
- Lesson: the new columns of 0007 and 0009 have Python defaults only, so the previous release
  could not insert rows while the migrations ran (the deploys went through without failed writes).
  `docs/recipes/new-migration.md` now asks for database defaults (`db_default`).
- Docs: glossary (Period, Schedule), AGENTS.md game rules, `docs/architecture/api-conventions.md`,
  `docs/plans/monthly-challenges.md` marked as superseded for periods.
- Left for stage 4's migration: require a period kind on proposals in the period constraint, once
  no release writes an empty one.

### Stage 4 - Month windows

- `windows()`: calendar months; allowed only in periods counted in months.
- Wizard: "N times a month" and "a total per month"; `describe.ts`.
- Tests: months of 28-31 days, a 3-month period, a late start in the first month.

### Stage 5 - Showing windows

- API: the Today card's `progress` is replaced by `window` (`first`, `last`, `need`, `full_need`,
  `done`, `state`); `GET /api/v1/challenges/{id}/windows?start=YYYY-MM-DD` lists a challenge's
  windows for the viewer, or for a start the admin is considering (one endpoint for the challenge
  page and the schedule sheet, so the app never computes needs itself).
- Frontend:
  - Today card: "1 of 2 this week" and a tag "Short week - Thu-Sun - 2 instead of 3";
  - challenge page: the list of windows with their needs and verdicts;
  - schedule sheet: "October starts on a Thursday, so the first week asks for 2";
  - leave sheet: what the last window then asks for;
  - one i18n key family for the phrases (`windows.short.*`), in Romanian and English.
- Removed: `ProgressOut`, its `KindEnum` override in `config/settings/base.py`, `days.Progress`,
  the `checkins.progress.*` keys (replaced, not kept beside the new ones).
- Tests: the tag only on short windows; amounts; the schedule note for a late start.
- Docs: `docs/design-system.md` if a new shared piece appears (likely a small `Tag`).

## Removal checklist

Everything this plan makes unused, and the stage that deletes it. A reviewer checks the stage's
rows are gone before approving.

| Item | Where | Stage |
|---|---|---|
| `next_month_of` (done) | `apps/challenges/periods.py` | 0 |
| Second `ChallengeNotFound` (done) | `apps/checkins/services.py` | 0 |
| `challenges.until`, `challenges.open`, `challenges.facts.{period,proposed,chosen,votes}` (done) | i18n | 0 |
| `DaySheetRow`, `useMemberProgress`'s `month` argument (done) | `features/checkins/api.ts` | 0 |
| Goal glossary row, `goal_target` example (done) | docs | 0 |
| `FIXED`, `week_quota`, `done_between`, `week_of`, frequency branches (done) | `apps/checkins/days.py` | 1 |
| Old weekly tests in `test_days.py` (done) | tests | 1 |
| `rule_of` (done) | `apps/challenges/windows.py` | 2 |
| `Frequency`, `TargetScope`, old fields in the model (done) | model | 2 |
| `TIMES_MAX`, `_days_needed` (done) | `apps/challenges/services.py` | 2 |
| Target i18n keys, `oncePerPeriod` (done) | i18n | 2 |
| Weekly-quota code in `seed_demo_history` (done) | seed | 2 |
| Old columns in the database (done) | migration | 3 |
| `PeriodKind.CUSTOM`, `PeriodKindNotAvailable`, its code and i18n key (done) | model, services, i18n | 3 |
| `period_kind` in `ScheduleIn` and `useSchedule` (done) | API, frontend | 3 |
| Month bounds and date-range loops recomputed (done) | `apps/checkins`, `windows.py`, `days.py` | 3 |
| `months.ts` and the frontend date-math copies (done) | frontend | 3 |
| "month" wording in schedule texts and period errors (done) | i18n, services | 3 |
| `ProgressOut`, `KindEnum` override, `days.Progress`, `checkins.progress.*` | API, settings, i18n | 5 |

## Out of scope

Repeating periods, every N days, a crew-chosen week start, `excused` days (they will lower a
window's need), judging early, push notifications, and everything about the wheel itself.

## Risks

| Risk | Answer |
|---|---|
| Judging is wrong around midnight or DST | The engine only sees crew-local dates; time-machine tests at 23:59 / 00:01 and on October 25, 2026. |
| The production challenge changes | Stage 1 golden tests; stage 2 owner checks before and after; migrations are reversible. |
| API changes break the app | The generated client turns them into compile errors; stages 2, 3 and 5 change the frontend in the same pull request. |
| Short weeks surprise people between stages 1 and 5 | Production has no weekly challenge; stage 5 can follow stage 1 directly if one is scheduled. |
