# Glossary

Use these words exactly - in code (models, functions, variables), API fields, UI translation keys,
and docs. If you need a new domain word, add it here in the same pull request.

| Term | Code name | Meaning |
|---|---|---|
| Crew | `Crew`, `crew`, `crew_id` | A group of people who challenge each other (a family, friends, a team). Not "family" or "group" (`Group` clashes with Django's auth model). UI: "Crew" / ro: "Echipa". |
| Member | `Member` | A user's membership in one crew. Holds display name and role. A user can be a member of several crews. |
| Role | `Member.role` | `admin` (can invite, choose the next challenge) or `member`. |
| Invite | `Invite` | A one-time code/link that lets a new person join a crew. |
| Pending invite | `list_pending_invites` | An invite nobody has used and that has not expired. Admins see these and can revoke them. |
| Revoke | `revoke_invite` | An admin cancels a pending invite; its link stops working at once (the row is deleted). |
| Join with account | `join_with_account` | Someone who already has an account (from another crew) joins a crew through an invite. |
| Active crew | `active_crew_id` (session), `Member.last_active_at` | The crew a user in several crews acts in. Chosen in Me; the most recent choice opens after the next login. |
| Pool | `selectors.pool`, `Crew.max_proposals` | The crew's proposals waiting to be scheduled. Holds at most `max_proposals` (default 50). |
| Proposal | `Challenge` with `state=proposed` | A challenge in the pool. Visible only to the crew, with who proposed it and when. |
| Vote | `Vote` | A member likes a proposal: one vote per member per proposal, for as many proposals as they want. |
| Period | `period_kind`, `period_length`, `period_start`, `end_date` | When a challenge runs. The creator proposes how long (`period_kind` months, weeks or days, and `period_length` how many); an admin picks the start; the end follows. |
| Schedule | `schedule_challenge` | An admin takes a proposal out of the pool and picks when it starts: the 1st of a month, a Monday, or any day from tomorrow (by its period kind). A month or week already under way starts tomorrow. Votes guide, they do not decide. Several challenges can run at the same time. |
| Challenge | `Challenge` | A shared task for a period. State: `proposed` -> `chosen` (and back, before the start). Phase of a chosen one (derived from dates): `upcoming`, `active`, `finished`. |
| Participant | `Participant` | A member who takes part in a challenge, chosen by its creator when proposing (the whole crew by default, the creator always). Sees it, votes on it while it is a proposal, checks in once it runs. Opting out before the start removes the row; leaving during it sets `left_on`. Not `Invite` (joining a crew). |
| Challenge day | `day` | A local calendar date in the crew's time zone. Deadline is local midnight. |
| Check-in | `CheckIn` (not "Checkin") | What a participant recorded for one challenge on one day (today only). Status: `done`, or `in_progress` (a number below the day's target); later `excused`. A missed day has no row: it is derived. |
| Entry | `CheckInEntry` | One "+N" of a check-in; a day's entries add up. Undo removes the last one. |
| Day state | `days.DayState` | How a day looks for one participant and challenge: `done`, `partial`, `todo`, `open`, `missed`, `not_due`, `future`, `outside`. |
| Due day | `days.is_due` | A day a challenge judged day by day (daily or chosen weekdays) asks for. Challenges asked a number of times or a total per week or period have no due days: they are judged per window. |
| Window | `windows.Window` | A stretch of days judged as one unit: a single day, a Monday-Sunday week, a calendar month (only in periods counted in months), or the whole period (`apps/challenges/windows.py`). |
| Requirement | `window`, `on_days`, `need_kind`, `need_value`, `day_min` | A challenge's rule: the window it is judged in, the weekdays that count (`on_days`, day windows only; empty = every day), what each window needs (`count` check-ins or an `amount` total) and, for counted numbers, the least amount a check-in needs (`day_min`). |
| Need | `Window.need` | What one window asks for: a number of check-ins or a total amount. |
| Short window | `Window.need` < `Window.full_need` | A window cut by the period's edges, a late start or leaving; it asks for less, in proportion to its days that count (rounded half up; amounts to one decimal). A window that would ask for nothing is not judged. |
| Verdict | `days.Verdict` | How a window stands: `met` (reached its need, even before it ends), `failed` (ended below it), `open` (today is in it), `future`. A failed day window is a missed day. |
| Proof | `Proof` (`apps/proofs`) | A `photo` or `video` backing a subject: today's check-in (added after checking in), later a spun punishment. At most 5 per subject. Status: `uploading`, `processing`, `ready`, `failed`. Removable only on the day it was added. |
| Proof subject | `Proof.subject` | What a proof backs, by a generic key (`subject_type` + `subject_id`); the subject's app starts and resumes its proofs. |
| Upload | `Upload` | One file the browser sends straight to the media bucket: one presigned PUT (photos) or a resumable S3 multipart upload (videos). Status: `uploading`, `complete`, `failed`. Must complete before `expires_at`. |
| Rendition | `Transcode` (`hls_key`, `poster_key`) | Processed versions of a video for playback (HLS 720p/360p + poster image), made by a MediaConvert job that Celery polls. |
| Grace period | `UPLOAD_GRACE` | 24 hours after the day's deadline for a proof's upload to finish (`Upload.expires_at`). |
| Feed | `selectors.feed` | The crew's check-ins with their proofs on challenges you can see, latest activity first (the check-in or its newest proof). Derived, nothing stored. UI: "Activitate" on Echipa. |
| Day sheet | `selectors.day_sheet` | One day of a challenge: every participant's state, total and proofs. Opened by tapping a day on the board. |
| Streak | `days.streak` | Per challenge: windows met in a row (due days, or weeks), counting back from the newest; the window still open today never breaks it. Challenges judged over the whole period have progress instead. |
| Flame tier | `flame_tier` | Derived from the streak: `ember` 1-2, `flame` 3-6, `blaze` 7-13, `blue` 14-29, `legendary` 30+. After v1. |
| Garden | - | Home screen showing every member's tree. After v1. |
| Tree stage | `tree_stage` | Derived from done days this challenge: `seed` 0, `sprout` 1-3, `sapling` 4-9, `bloom` 10-19, `fruit` 20+. After v1. |
| Wilted | `wilted` | A tree's look while its member has an unserved punishment. After v1. |
| Greenhouse | - | Archive of past months' trees. After v1. |
| Reaction | `Reaction` | One member's emoji on something in the crew (v1: a check-in card in the journal). One per member per target; picking another replaces it. |
| Reaction target | `target` | A kind of thing that takes reactions, registered by its app (`check_in` now). |
| Punishment | `Punishment` | One of a challenge's punishments: a short text and whether it needs proof. None, or 2 to 8, written by the creator; fixed once scheduled. |
| Spin | `Spin` | One turn of the wheel owed for one missing check-in (or one missed total) in a failed window. Status (derived): `pending` (not spun), `spun` (drawn, not served), `served`. |
| Wheel of Doom | `doom` app | Punishments for failed windows: spins are owed, drawn on the server, then served with proof (`docs/plans/wheel.md`). |
