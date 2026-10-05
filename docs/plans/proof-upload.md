# Plan: proof upload (stage 3, the last v1 step)

Status: draft for review. Branch: `feat/proofs` from `feat/check-ins`.
Priorities, in order: efficiency (fast on a phone, cheap to run), user experience, architecture.

## Decisions (agreed)

| Topic | Decision |
|---|---|
| Does a day need proof? | No. The check-in makes the day done; proof is extra. A day with proof gets a dot on the board and in the week strip. `proof_required` only nudges ("Adauga dovada") on the card. |
| How many | Up to 5 proofs per check-in (photos and/or videos, as the challenge's `proof_kind` allows). |
| Deleting | Only today: you can remove a proof (and add another) until midnight. After that proofs are permanent. |
| Where the crew sees them | A feed on Echipa (who checked in what, when, with which proofs), and a day sheet: tap a day on a challenge's board to see everyone's proofs for that day. |

## Decisions with a proposed default (confirm or change)

1. **Proof comes after the check-in.** The card shows "Adauga dovada" once you have checked in
   (hold, or a number). One rule, no hidden check-ins. The upload can start right after the hold.
2. **Photos are shrunk on the phone** to at most 2048 px, JPEG ~0.8 (usually 300-700 KB instead of
   3-8 MB), with a 480 px thumbnail made at the same time. Both go up with one presigned PUT each.
   No server work for photos at all.
3. **Videos are uploaded as they are** (multipart, resumable, up to 20 GB, per AGENTS), with a
   poster frame grabbed on the phone so the feed shows something at once. MediaConvert makes HLS
   (360p + 720p) and a poster in the background; the original stays as the fallback.
4. **MediaConvert is polled, not called back.** A Celery task checks the job every 20 s (then
   backs off) until it is done or failed. No EventBridge/SNS/webhook to set up or secure.
   Remove `MEDIACONVERT_WEBHOOK_SECRET` from `.env.example` and the settings (no longer used).
5. **Viewing.** Production: private bucket behind CloudFront with signed cookies scoped to the
   crew's folder (one cookie set covers photos and every HLS segment), on a subdomain of the app
   (`media.<domain>`). Local: presigned GET URLs from the dev bucket, and videos play the
   original file. Both behind one adapter, so screens do not know the difference.
6. **The feed is derived, not stored**: one item per check-in (member, challenge, day), ordered by
   its latest activity (the check-in or its newest proof), with the proofs' thumbnails. 30 per page,
   cursor paging. Refreshes on focus and every 60 s while visible.
7. **New dependencies** (each with its reason in the PR): `zustand` (the upload manager outlives
   screens), `@uppy/core` + `@uppy/aws-s3` (multipart engine: parallel parts, retries, resume),
   `hls.js` (HLS on Android/desktop; lazy-loaded, Safari plays HLS natively), `idb-keyval`
   (resume data in IndexedDB, 600 bytes).

This replaces one line of `docs/architecture/overview.md` ("the phone creates a check-in
(`uploading`)"): the check-in exists first, and the proof attaches to it. Updated in commit 3.

## Data

`apps/media` (new, low level, knows nothing about challenges):

| Model | Fields | Notes |
|---|---|---|
| `Upload` | crew, key, content_type, size, fingerprint, `mode` (single / multipart), upload_id, status (`uploading`, `complete`, `failed`), parts (JSON: number -> etag), expires_at, completed_at, deleted_at | One file in the bucket. The caller makes the key on the server (`crews/<crew>/proofs/<proof>/original.<ext>`) and sets `expires_at` (for a proof: 24 h after the day's deadline). Soft deleted: deleting removes the file and keeps the row. |
| `Transcode` | upload, job_id, status (`running`, `done`, `failed`), hls_key, poster_key, checked_at | Videos only. |

`apps/checkins` gains:

| Model | Fields | Notes |
|---|---|---|
| `Proof` | crew, check_in, kind (`photo` / `video`), original (Upload), thumb (Upload, nullable), status (`uploading`, `processing`, `ready`, `failed`), created_at | At most 5 per check-in (not counting failed). Soft deleted (AGENTS: proofs are kept): removing one today hides it and deletes its files. The member is the check-in's. Width, height and duration come when the viewer needs them. |

Layers: `checkins` uses `media` services; `media` uses `integrations/storage` and a new
`integrations/transcoding` (MediaConvert) and `integrations/cdn` (signed cookies or presigned
URLs). Import-linter: `media` sits below `checkins`; only `integrations/*` import boto3.

## Rules (services)

- `start_proof(by, challenge_id, day, kind, content_type, size, fingerprint)`: today only, you
  have checked in, the kind is allowed, fewer than 5, size <= 20 GB, type on the allow list
  (jpeg/png/webp/heic for photos; mp4/quicktime/webm for videos). Returns the presigned PUT URL(s)
  for photos, or the upload id and part size for videos (16 MiB under 1 GiB, 64 MiB above).
- `sign_parts`, `record_part(number, etag)`, `complete_proof`: complete is allowed until 24 h after
  that day's midnight (AGENTS). Complete does HeadObject (size must match), then a photo is
  `ready`, a video goes `processing` and a MediaConvert job is queued.
- `resume_proof(fingerprint)`: the open upload with that fingerprint and its recorded parts.
- `delete_proof(by, proof_id)`: today only, your own; soft delete, and aborts or deletes the files.
- Celery: `poll_transcode(transcode_id)` (idempotent, retries with backoff, gives up after 2 h),
  `expire_uploads` every 15 min (uploading past the 24 h grace -> abort + `failed`).

## API

```
POST   /api/v1/challenges/{id}/check-ins/{day}/proofs   start: {kind, content_type, size,
                                                        fingerprint} -> proof + upload plan
POST   /api/v1/proofs/{id}/parts                        {numbers} -> fresh part URLs
PUT    /api/v1/proofs/{id}/parts/{number}               {etag} report a finished part
POST   /api/v1/proofs/{id}/complete                     -> proof (ready or processing)
GET    /api/v1/proofs/resume?fingerprint=...            -> proof + uploaded parts, or 404
DELETE /api/v1/proofs/{id}                              today only, your own -> 204
GET    /api/v1/challenges/{id}/days/{day}               everyone's state, amount and proofs
GET    /api/v1/feed?before=...                          the crew's recent check-ins with proofs
POST   /api/v1/media/session                            sets the CloudFront cookies (no-op locally)
```

`GET /today` cards and the board rows gain `proofs` / `proof_days` so the dot and the card need no
extra request.

## How it looks and feels

1. **On today's card**, after the check-in: a row of up to 5 square thumbnails and a "+" tile.
   "+" opens the phone's picker (camera or gallery, by the challenge's proof kind). The new tile
   appears at once with the local preview and a progress ring; tap it while uploading to pause or
   retry, after upload to view. "x" removes it (today only, with undo in the toast).
2. **Uploads never block.** The upload manager is global: you can leave the screen; the raised
   check-in button shows a thin progress ring and a count while anything uploads. Screen Wake Lock
   while uploading; pauses offline and resumes online; a big video on a phone (> 2 GB) asks first.
   If the app is closed mid-video, picking the same file again resumes from the last part.
3. **The Echipa feed** ("Activitate", under the members): "Ana a bifat Plimbare", time ("acum
   5 min", "ieri 21:40"), up to 3 thumbnails (+N). A video shows its poster with a play mark;
   while processing a soft "Se pregateste" overlay. Tap an item: the viewer.
4. **The day sheet**: tap a day on the board (or a feed item) -> "Luni, 5 octombrie": each person
   with their state and their proofs. Tap a proof: full-screen viewer, swipe between proofs,
   video plays inline (HLS, muted until tapped), pinch to zoom photos.
5. **The dot**: a small dot under a day in `DayBars` and `WeekStrip` when there is at least one
   proof. Readable by shape, not color.

New `shared/ui` pieces (on `/design` and in `docs/design-system.md` first): `ProofTile`
(thumbnail with progress, processing, failed, video states), `ProofViewer` (full screen,
swipe), `FeedItem`, and the dot in `DayBars` / `WeekStrip`.

## Efficiency budget

- A photo proof: ~0.5 MB up, two PUTs, two API calls. Visible to the crew as soon as it lands.
- A video: parts of 16/64 MiB, 4 in parallel, 6 retries; the API is called once per part (ETag).
- Thumbnails everywhere (480 px); full images and HLS only in the viewer. hls.js only loads there.
- Feed: one query with `select_related` + one prefetch for proofs; indexed by (crew, created_at).
- Nothing in the service worker cache (network-only for media, per AGENTS).

## Infra (written as JSON for the owner to apply; never applied by an agent)

`infra/aws/`: S3 CORS (PUT from the app origin, expose `ETag`), lifecycle (abort incomplete
multipart after 7 days), CloudFront distribution + key group + origin access control,
MediaConvert role, IAM policy updates for `cc-prod-app` and `cc-dev`. `environments.md` updated.
A smoke test (`make upload-smoke`) uploads a small and a multipart file to the dev bucket and
checks the object.

Done for dev (by the owner, `infra/aws/README.md`): bucket CORS, lifecycle, `cc-dev` user,
`cc-mediaconvert-dev` role. Production documents (`infra/aws/prod/`) come with stage 3, next to
the code that uses them (cookie scope, key pair id and job settings must match that code).

Proposed (confirm in stage 3): the MediaConvert job settings (HLS 360p/720p + poster) live in
`integrations/transcoding` as code instead of a console job template: versioned and reviewed with
the code, tested against the in-memory fake, nothing to keep in sync in the console.

## Edge cases

| Case | Behaviour |
|---|---|
| Upload starts 23:59, finishes 00:30 | Counts for yesterday (started before midnight, within 24 h). |
| App killed mid-video | Next time the same file is picked: resume from the recorded parts. |
| Presigned URLs expire mid-upload | The engine asks for fresh ones (`/parts`). |
| Phone goes offline | Paused, resumes when online; the tile says "In asteptare". |
| 6th proof | The "+" tile is gone; the API refuses too. |
| Proof kind is photo only | The picker only offers images; the API refuses a video. |
| Transcoding fails | The proof shows the original (if the browser can play it) or "Nu s-a putut pregati". |
| Leaving a challenge | Proofs stay with the check-ins; the crew still sees them on the board. |
| Deleted after midnight | Not possible (permanent). |
| Undo removes the day's last entry | The check-in goes, and its proofs and files with it. |
| Thumbnail never arrives | Complete drops it; the original stands in. |
| HEIC from an iPhone | Safari hands JPEG to the page when we ask for images; we accept HEIC anyway. |

## Stages

Each stage ends with `make check` green and is reviewed before the next one starts. Backend
stages come first, so the frontend builds on a finished API.

| Stage | Commits | What works at the end |
|---|---|---|
| 1. Upload backbone | `feat(backend): add uploads with presigned parts and resume` | `apps/media`: `Upload`, start (one PUT or multipart), sign, record parts, complete with a size check, delete. Storage adapter: presigned PUT, delete. `make upload-smoke` checks the S3 side. No API yet. |
| 2. Proofs on check-ins | `feat(backend): attach proofs to check-ins` | `Proof`; start / parts / complete / resume / delete endpoints; 5 max, kinds and types, today only, 24 h grace; expiry job; `proofs` / `proof_days` on today and the board; thumbnails by presigned GET (the local half of the media link adapter). Photos work end to end in the API. |
| 3. Videos and production media | `docs(infra): add the s3, cloudfront and mediaconvert setup for proofs`, `feat(backend): transcode videos and sign media links` | Production `infra/aws/` documents; `Transcode` + `poll_transcode`; CloudFront signed cookies + `POST /media/session`; `overview.md` and `.env.example` without the webhook. |
| 4. Feed and day view | `feat(backend): add the crew feed and the day view` | `GET /feed`, `GET /challenges/{id}/days/{day}`. |
| 5. Shared UI | `feat(frontend): add proof tile, viewer and feed item to shared ui` | `ProofTile`, `ProofViewer`, `FeedItem`, the dot; on `/design` and in `docs/design-system.md`. |
| 6. Uploading | `feat(frontend): upload proofs from the check-in card` | Upload manager (Zustand, Uppy), photo shrink + thumbnail, resume, wake lock, offline pause, progress on the tab bar. |
| 7. Seeing proofs | `feat(frontend): show the crew feed on echipa and the day sheet on the board`, `test(frontend): cover proof upload end to end` | Echipa feed, day sheet, e2e; then the multi-GB upload with a network cut on a real phone. |

## Tests that must exist

- Services: today-only start, 24 h grace on complete, 5 max, kinds and types, size check on
  complete, resume by fingerprint, delete only today and only your own, expire job twice is safe.
- Transcode polling: done, failed, retried; never two jobs for one proof.
- Feed and day view: only challenges the viewer can see; paging is stable.
- Frontend: photo shrink + thumbnail, progress and retry, offline pause, resume, the dot, viewer
  swipe, reduced motion.
- Before calling it done (AGENTS): a multi-GB upload with a network cut and a resume, on a real
  phone (`make preview`).

## Out of scope

Reactions and comments on proofs, push notifications, proof editing (trim/crop), downloading.
