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
| Schedule | `schedule_challenge` | An admin takes a proposal out of the pool and sets its period (v1: a month). Votes guide, they do not decide. Several challenges can share a period. |
| Challenge | `Challenge` | A shared task for a period. State: `proposed` -> `chosen` (and back, before the start). Phase of a chosen one (derived from dates): `upcoming`, `active`, `finished`. |
| Participant | `Participant` | A member who takes part in a challenge, chosen by its creator when proposing (the whole crew by default, the creator always). Sees it, votes on it while it is a proposal, checks in once it runs. Opting out before the start removes the row; leaving during it sets `left_on`. Not `Invite` (joining a crew). |
| Challenge day | `day` | A local calendar date in the crew's time zone. Deadline is local midnight. |
| Check-in | `CheckIn` (not "Checkin") | What a participant recorded for one challenge on one day (today only). Status: `done`, or `in_progress` (a number below the day's target); later `excused`. A missed day has no row: it is derived. |
| Entry | `CheckInEntry` | One "+N" of a check-in; a day's entries add up. Undo removes the last one. |
| Day state | `days.DayState` | How a day looks for one participant and challenge: `done`, `partial`, `todo`, `open`, `missed`, `not_due`, `future`, `outside`. |
| Due day | `days.is_due` | A day a daily or chosen-weekday challenge asks for. Challenges asked a number of times per week or period have no due days, only a quota. |
| Proof | `Proof` | What backs a check-in: a `photo` or `video` (v1), at most 5 a day, added after checking in. Status: `uploading`, `processing`, `ready`, `failed`. Removable only on its own day. Later also for a served punishment. |
| Upload | `Upload` | One file the browser sends straight to the media bucket: one presigned PUT (photos) or a resumable S3 multipart upload (videos). Status: `uploading`, `complete`, `failed`. Must complete before `expires_at`. |
| Rendition | `hls_key`, `poster_key` | Processed versions of a video for playback (HLS 720p/360p + poster image). |
| Grace period | `UPLOAD_GRACE` | 24 hours after the day's deadline for a proof's upload to finish (`Upload.expires_at`). |
| Streak | `days.streak` | Per challenge: due days in a row without a miss (daily, weekdays) or weeks in a row with the quota met (times a week). Today never breaks it. |
| Flame tier | `flame_tier` | Derived from the streak: `ember` 1-2, `flame` 3-6, `blaze` 7-13, `blue` 14-29, `legendary` 30+. After v1. |
| Garden | - | Home screen showing every member's tree. After v1. |
| Tree stage | `tree_stage` | Derived from done days this challenge: `seed` 0, `sprout` 1-3, `sapling` 4-9, `bloom` 10-19, `fruit` 20+. After v1. |
| Wilted | `wilted` | A tree's look while its member has an unserved punishment. After v1. |
| Greenhouse | - | Archive of past months' trees. After v1. |
| Goal | `goal_label`, `goal_target` | Optional numeric monthly target of a challenge (e.g. "books", 2). |
| Reaction | `Reaction` | An emoji another member puts on a proof. After v1. |
| Punishment | `Punishment` | An entry in the crew's pool of forfeits. After v1. |
| Spin | `PunishmentSpin` | One pending or completed turn of the Wheel of Doom for one missed day. Status: `pending`, `spun`, `served`. After v1. |
| Wheel of Doom | `doom` app | The feature that assigns a punishment after a missed day. After v1. |
