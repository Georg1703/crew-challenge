# Product plan

The source of truth for how the game works. Code must follow these rules; if a rule needs to change,
change it here first (and in the root `AGENTS.md` if it is listed there).

## Vision

A PWA for a small group of people - a **crew** - who set one shared challenge each month and
check in daily with proof. It should be fun enough that people *want* to open it: every action has
a satisfying animation, the home screen is a living garden, and missing a day has a playful cost.
The first crew is the owner's family; any group can use it.

## Game rules

1. **Rotation.** Members have a fixed order. Each month exactly one member - the next in the
   rotation - is the proposer for the following month. The order wraps around.
2. **Proposal window.** The proposer drafts the challenge near the end of the month and must
   publish it by the crew's deadline (for example the 28th at 21:00). Only the proposer can create
   or edit it.
3. **Reveal.** A published challenge is *sealed*: everyone sees a card with a countdown, and it
   flips open for all members at the same moment (for example on the last evening of the month).
   It becomes active at 00:00 on day 1.
4. **Challenge definition.** Title, description, frequency (daily in the MVP), required proof
   type(s), and an optional monthly goal (for example "2 books").
5. **Daily check-in.** A day counts when the member submits proof before local midnight. The
   check-in is recorded when the upload *starts*, so a slow upload never costs the day.
6. **Grace for uploads.** An `uploading` check-in has 24 hours after the deadline to finish.
   If the upload never completes, the day becomes missed.
7. **Missed day.** At 00:05 the system marks missing days, resets the streak, wilts the member's
   tree, and gives them one pending Wheel of Doom spin per missed day.
8. **Punishment.** The member spins, gets a punishment from the crew's pool (chosen by the server
   before the animation), and marks it served with proof. The tree recovers when it is served.

Open rule questions (to be decided by the crew): what happens if the proposer misses the deadline
(suggested: they spin the wheel and the next person proposes), and whether a sick or travelling
member can be excused for a day.

## MVP scope

| Feature | Scope |
|---|---|
| Crew, members, invite link, login | MVP |
| Proposer rotation, create/publish challenge | MVP |
| Reveal animation (sealed card, countdown, synchronized flip) | MVP |
| Daily check-in with proof: video, audio, photo, text | MVP |
| Direct-to-S3 multipart uploads up to 20 GB, resumable, non-blocking | MVP |
| MediaConvert transcoding to HLS, playback via CloudFront | MVP |
| Streak flames (5 tiers) and calendar history | MVP |
| Crew garden with growing trees (5 stages, wilt state) | MVP |
| Wheel of Doom and punishment pool | MVP |
| Emoji reactions on proofs | MVP |
| Web Push reminders (20:00, 23:00, "X just checked in") | MVP |
| Monthly goal progress | MVP |
| Peer verification of proofs | Later |
| Shields (skip-day tokens) | Later |
| Badges, month-end "Crew Wrapped" | Later |
| Transcription, compilation video | Later |
| Weekly / one-off challenges (UI) | Later |
| Several crews per person (crew switcher UI) | Later - the data model supports it from day one |

## Garden and streaks

- **Tree** per member, planted fresh on day 1 of each challenge. Stage from done days this month:
  seed (0), sprout (1-3), sapling (4-9), bloom (10-19), fruit tree (20+). A perfect month earns a
  golden fruit. Missed day -> wilted look with a rain cloud until the punishment is served.
  Built in Rive: number input `stage` (0-4), booleans `wilted` and `golden`, trigger `grow`.
- **Flame** shows the unbroken streak across challenges: ember (1-2), flame (3-6), blaze (7-13),
  blue fire (14-29), legendary (30+). Dim with a countdown when today is not done; sputters after 20:00.
- **Crew status row** under the garden: who checked in today, who is uploading, who has not yet.
- **Greenhouse** archives each month's trees.

## Wheel of Doom

- Every member can add punishments to the crew pool at any time.
- The server picks the result, then the client animates the wheel to land on it (ticking sound
  only after a user tap). Other members get a push and can watch the replay.
- The punished member uploads proof when it is served. Each missed day is its own spin.

## Media

- Uploads go straight from the browser to a private S3 bucket (multipart, presigned parts,
  resumable). Details and limits are in the root `AGENTS.md`.
- MediaConvert produces HLS (720p + 360p) and a poster image. CloudFront with signed cookies
  serves playback; iOS plays HLS natively, other browsers use hls.js.
- Audio is normalized to AAC `.m4a`; HEIC photos are converted to JPEG/WebP.
- Originals move to Glacier Instant Retrieval after 30 days.

## Screens

Home/Garden - Check-in sheet - Feed - Challenge - Profile (flame, calendar, greenhouse) -
Wheel of Doom - Proposer studio - Reveal - Install guide.

## Milestones

| Milestone | Dates (2026) | Outcome |
|---|---|---|
| M1 Foundations | Oct 1-5 | Deployed, installable app; crew, invites, login; agent-ready repo |
| M2 Core loop | Oct 6-12 | Challenges, check-ins, multipart uploads with resume |
| M3 Media & judgment | Oct 13-18 | MediaConvert pipeline, feed, reactions, midnight jobs, streaks, Wheel of Doom backend |
| M4 Delight | Oct 19-25 | Rive tree and flame, garden, wheel and reveal animations, Web Push, performance pass |
| M5 Launch | Oct 26-31 | Everyone installed; first proposer creates November's challenge; reveal on Oct 31 |
