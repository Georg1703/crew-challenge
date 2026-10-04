# Glossary

Use these words exactly - in code (models, functions, variables), API fields, UI translation keys,
and docs. If you need a new domain word, add it here in the same pull request.

| Term | Code name | Meaning |
|---|---|---|
| Crew | `Crew`, `crew`, `crew_id` | A group of people who challenge each other (a family, friends, a team). Not "family" or "group" (`Group` clashes with Django's auth model). UI: "Crew" / ro: "Echipa". |
| Member | `Member` | A user's membership in one crew. Holds display name, role, and rotation position. A user can be a member of several crews. |
| Active crew | session `active_crew_id` | The crew a user is acting in when they belong to several. Defaults to their oldest membership. |
| Role | `Member.role` | `admin` (can invite, reorder rotation) or `member`. |
| Invite | `Invite` | A one-time code/link that lets a new person join a crew. |
| Pending invite | `list_pending_invites` | An invite nobody has used and that has not expired. Admins see these and can revoke them. |
| Revoke | `revoke_invite` | An admin cancels a pending invite; its link stops working at once (the row is deleted). |
| Join with account | `join_with_account` | Someone who already has an account (from another crew) joins a crew through an invite. |
| Active crew | `active_crew_id` (session), `Member.last_active_at` | The crew a user in several crews acts in. Chosen in Me; the most recent choice opens after the next login. |
| Rotation | `Member.rotation_position` | The fixed order in which members take turns proposing challenges. |
| Proposer | `Challenge.proposer` | The member whose turn it is to create next month's challenge. |
| Challenge | `Challenge` | The shared task for one month. Status: `draft` -> `sealed` -> `active` -> `finished`. |
| Sealed | `Challenge.Status.SEALED` | Published by the proposer but hidden until the reveal. |
| Reveal | `reveal_at` | The moment a sealed challenge flips open for everyone. |
| Challenge day | `day` | A local calendar date in the crew's time zone. Deadline is local midnight. |
| Check-in | `CheckIn` (not "Checkin") | A member's completion of one challenge day. Status: `uploading`, `done`, `missed`, `excused`. |
| Proof | `Proof` | What backs a check-in or a served punishment: `video`, `audio`, `photo`, or `text`. |
| Upload | `MultipartUpload` | The S3 multipart upload that carries a proof's original file. |
| Rendition | `hls_key`, `poster_key` | Processed versions of a video for playback (HLS 720p/360p + poster image). |
| Grace period | `UPLOAD_GRACE` | 24 hours after the day's deadline for an `uploading` check-in to finish. |
| Streak | `current_streak`, `best_streak` | Consecutive days with a `done` check-in, across challenges. |
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
