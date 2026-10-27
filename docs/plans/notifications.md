# Plan: notifications (in the app and Web Push)

Status: built in one go on `feat/notifications` (2026-10-27) with the proposed defaults D1-D7
(the owner asked for all four stages at once). One change on the way: the unsubscribe call
takes the endpoint in the query string (a DELETE has no body in the generated client).

## Goal

A member learns that someone reacted to their card, commented on it, reacted to their comment
or answered it, without opening every card: a badge on the Crew tab, a list of news in the app,
and (installed on the home screen, with permission) a push notification when the app is closed.

One generic model carries all of it: any app can post a notification about any registered
target, and push is one more way the same row reaches its person. Reaction notifications and
Web Push are on the "after v1" list in `AGENTS.md`; this plan takes both.

## What changes for members

| | Today | After |
|---|---|---|
| Someone reacts to my card or my comment | Nothing, until I look at the card | A line in my news: "Ana reacted with (heart) to your check-in" |
| Someone comments on my card | The Crew tab badge counts it; the card says "1 new" | The same, plus a line in my news: "Ion: Super, bravo!" |
| Someone answers my comment | The Crew tab badge counts it | A line in my news: "Ana answered you: ..." |
| Someone comments on a card I commented on | The Crew tab badge counts it | A line in my news (default D2) |
| The Crew tab badge | Others' unread comments on what I posted or commented on | My unread news, whatever its kind |
| The news list | - | A bell on the Crew screen opens it: latest first, unread marked; a tap opens the card |
| Opening a card | Marks its comments read | Also marks every piece of news about it read |
| App closed (installed, permission given) | Nothing | A push notification with the same line; a tap opens the card |
| Me | - | "Notifications on this device": on or off; iPhone not installed: the install guide instead |

## Decisions

Proposed defaults, to confirm:

- **D1. Who is told.** A reaction or comment on a target tells the target's owner (the card's
  member; the comment's writer). A reply tells the comment's writer too. Never the actor, and
  one row per person per act: a reply to my comment on my own card is one line, "answered",
  not two.
- **D2. A comment on a card I commented on tells me** (kind `comment`, like the owner's), so
  the badge keeps counting what it counts today. Not a reply, not my own card: still news.
- **D3. Opening the news list marks it all read**; the badge drops to zero. Unread lines keep
  a dot until then. No per-line "mark read" (two states to explain for nothing).
- **D4. A reaction changed is the same news**, refreshed (the old row goes with the old reaction,
  a new one comes with the new); a reaction taken back takes its news with it. A comment deleted
  in its first minute takes its news with it.
- **D5. Push sends every notification**, once, in the person's language (`preferred_language`),
  to every device they turned it on. No quiet hours, no digest, no "skip if the app is open":
  the phone collapses lines about the same card (one `tag` per card), which is enough for a
  crew of a few people.
- **D6. News is kept 90 days**, then dropped by a nightly job (the list never grows past what
  a family reads).
- **D7. The old `GET /comments/unread` goes.** The badge reads the news' unread count; the
  per-card "3 new" from `CommentRead` stays as it is.

## Model

New app `apps/notifications`, generic like `apps/reactions` and `apps/comments`. It sits on
`crews` (members, the target registry) and nothing above: reactions and comments call it, it
imports neither.

```
Notification(CrewScopedModel)        # id, crew, created_at, updated_at
  recipient   FK Member, cascade     # whose news it is
  actor       FK Member, cascade     # who did it (name and avatar read live)
  kind        "reaction" | "comment" | "reply"
  source_type, source_id             # generic key: the Reaction or Comment that caused it
  target_type, target_id             # generic key: the page that shows it (a journal card)
  facts       JSON, frozen: {"emoji": ...} or {"text": "first 80 characters"}
  read_at     null until read
  index (recipient, -created_at)
  unique (recipient, source_type, source_id)   # one line per person per act

PushSubscription(TimeStampedModel)   # stage 3
  user        FK User, cascade       # a device belongs to the person, whatever crew is open
  endpoint    unique (the browser's push URL), p256dh, auth
  user_agent  short, for the Me list ("Safari on iPhone")
  failed_at   null; set when the push service says the subscription is gone, row then deleted
```

Two generic keys, each for one job:

- `source` is the row that caused the news. `Reaction` and `Comment` declare
  `notifications = GenericRelation("notifications.Notification", content_type_field=
  "source_type", object_id_field="source_id")`, so a reaction deleted or replaced takes its
  news with it (D4) with no code in `reactions`. A comment is soft deleted, so `comments.delete`
  calls `notifications.services.retract(source=comment)`.
- `target` is where a tap goes: a registered target the frontend has a page for (`entry` ->
  `/crew/cards/{id}`). A reaction on a comment sits on the comment's card, so the registry
  learns where a target is shown: `Target(..., page=...)`, a function from the object to
  `(key, id)`; `None` means itself. `comment` registers `page=lambda c: (targets.key_for(
  c.target_type), c.target_id)` and `owner="member"` (it has an owner today in all but name).

What is frozen: the emoji, the comment's first 80 characters. What is live: who (names change,
avatars change). The card itself is not read when the list is built: the line says "your
check-in" / "your comment" from `kind` and the target's key, nothing more; opening it shows
the card. ponytail: a card the recipient can no longer see (they left the challenge) still
lists; its tap shows the existing "not here any more" message.

## Services

```
notifications.services
  notify(*, kind, actor, source, recipients) -> None
      # recipients: members; the actor is dropped; one row each (get_or_create on source);
      # the page is targets.page_of(source.target); facts from the source (emoji / text);
      # on commit: tasks.push.delay(notification_id) for each row (stage 3)
  retract(*, source) -> None            # the source is gone (soft deleted): its news goes
  mark_read(*, member, target=None)     # everything (the list opened) or one card's (opened)
  prune() -> int                        # nightly: rows older than 90 days (D6)

notifications.selectors
  page(*, member, before=None, limit=30) -> list[Notification]  # latest first, actor joined
  unread_count(*, member) -> int

reactions.services.react      -> notify(kind="reaction", actor=member, source=reaction,
                                        recipients=[targets.owner_of(obj)])
comments.services.add         -> notify(kind="reply" if parent else "comment", ...,
                                        recipients=[owner, parent.member, *other writers (D2)])
                                 # one call: a member in the list twice gets one row; the kind
                                 # is "reply" for the parent's writer, "comment" for the rest
comments.services.delete      -> retract(source=comment)
comments.services.mark_read   -> notifications.services.mark_read(member=member, target=found)
```

`targets.owner_of(obj)` reads `Target.owner`; a card with no member (the crew's day) has no
owner and nobody is told. Registry additions: `page`, `page_of(obj)`, `key_for(content_type)`,
`owner_of(obj)`; a test checks every registered model with an owner names a real field.

## API

```
GET  /api/v1/notifications?before=<iso>      -> {"results": [NotificationOut], "unread": n}
PUT  /api/v1/notifications/read              -> 204  (everything, D3)

NotificationOut: id, kind, actor: MemberBriefOut, target: {"type": "entry", "id"},
                 facts: {emoji?, text?}, created_at, read_at
```

One endpoint for the list and the badge: the Crew tab asks it every 60 s and on focus (as the
comment badge does today) and reads `unread`; the list screen reads `results`. ponytail: the
badge pulls 30 rows a minute per open app; a `/unread` count endpoint when that is measured
to matter. `comments/unread` and `useUnreadCount` go (D7).

Stage 3 adds:

```
GET    /api/v1/push/key                      -> {"public_key": VAPID}   (empty: push is off)
PUT    /api/v1/push/subscriptions            {endpoint, keys: {p256dh, auth}} -> 204 (upsert)
DELETE /api/v1/push/subscriptions?endpoint=  -> 204
```

## Push (stages 3 and 4)

Backend:
- `integrations/push/`: `PushSender` ABC with `send(subscription, payload) -> Sent | Gone`,
  `WebPushSender` (pywebpush, VAPID from settings), `InMemoryPushSender` for tests, a factory
  on `PUSH_BACKEND` = `webpush` | `memory` | `off` (default locally). Only this package
  imports `pywebpush` (import-linter already says so). New dependency `pywebpush`
  (`py-vapid` comes with it): the Web Push protocol with VAPID signing and payload encryption,
  not something to write by hand.
- `notifications.tasks.push(notification_id)`: loads the row, builds `{title, body, url, tag}`
  in the recipient's language (`preferred_language`; the texts live in a small dict in
  `notifications/texts.py`, ro and en), sends to each of the user's subscriptions; `Gone`
  (404 / 410) deletes the subscription. Idempotent enough: a retry sends the same line twice,
  which the `tag` collapses on the phone. Queued with `transaction.on_commit` from `notify`.
- `url` = `/crew/cards/{id}?crew={crew_id}`: the person may have another crew open.
- Keys: the owner makes a VAPID pair once (`make vapid-keys`) and puts it in the server's
  `.env` (`VAPID_*` are already in `.env.example`). Without keys push is off, the API says so,
  the Me switch hides.

Frontend:
- The service worker moves from `generateSW` to `injectManifest` (`src/pwa/sw.ts`): the same
  precache and navigation fallback, written out (about 15 lines of Workbox), plus `push`
  (`showNotification(title, {body, tag, data: {url}})`) and `notificationclick` (focus an open
  window and navigate it, or open one). The SW never touches `/api`.
- `features/notifications/push.ts`: `subscribe()` after a user gesture: permission, then
  `pushManager.subscribe({userVisibleOnly: true, applicationServerKey})`, then `PUT`;
  `unsubscribe()` the reverse. On every app start with permission granted: re-`PUT` the
  current subscription (browsers rotate endpoints; the server upsert is cheap).
- Where it is asked: a "Turn on notifications" line on Me (switch); and once, after the first
  check-in post ever on this device (`localStorage` flag), a small card under the confetti:
  "Want to know when the crew reacts?" (AGENTS: after the first check-in, never on first load).
  iPhone in Safari (not installed): the switch shows the install guide instead; iOS 16.4+
  installed: it works. Permission denied: the switch is off and says so.
- `?crew=` on the URL: `RequireAuth` switches the active crew before rendering when it differs
  from the one open (the switch endpoint exists; `enterCrew` refetches everything).

Not here: a read receipt from the phone back to the server (tapping a push does not mark the
line read; opening the card does), badges on the app icon (`navigator.setAppBadge`: one line
in stage 4 if the owner wants it), notification sounds.

## Stages

Each stage: `make check` green, the docs it touches updated in the same commit.

**Stage 1 - the news, backend.** `apps/notifications` (model, services, selectors, API,
admin), registry `page` / `owner_of` / `key_for`, `comment` target gets `owner`, hooks in
`reactions.services` and `comments.services`, `comments/unread` removed, `prune` beat job,
`make schema`. Tests: each kind reaches the right people and never the actor; one row per
act; replaced reaction refreshes, taken back removes; deleted comment retracts; opening a card
reads its news; the list pages; prune. Docs: `backend.md` (app list, layers), `glossary.md`
(Notification, News, kind), `api-conventions.md` if the list shape is new.

**Stage 2 - the news, frontend.** `features/notifications`: `useNews` (list + unread, 60 s),
`useMarkNewsRead`; `NewsRoute` at `/crew/news` (full screen, like the card page) with a row
per line (avatar, text with the actor in bold, relative time, unread dot) and empty state;
the bell with the count on the Crew screen; the tab badge from `unread`; `comments.badge`
key renamed. Tests: rendering of each kind, read on open, tap routes to the card.

**Stage 3 - push, backend.** `PushSubscription`, `integrations/push`, the three endpoints,
the Celery task, texts, settings and `.env.example` note on making keys; pywebpush added.
Tests with the in-memory sender: one send per device, gone subscription dropped, off means no
task, language picked. `environments.md`: the keys, production `.env`.

**Stage 4 - push, frontend.** `injectManifest` SW, `push.ts`, the Me switch, the after-first-
check-in card, `?crew=` switching, i18n. Checked by hand on an Android phone and an installed
iPhone over `make preview` (push needs HTTPS: the tunnel gives it).

## Open questions for the owner

1. D2: does a comment on a card you commented on count as news? (Keeps today's badge rule.)
2. D3: opening the list reads everything, or each line on its tap?
3. Push: all four kinds, or reactions in the app only (comments and replies by push)?
4. The after-first-check-in card: wanted, or only the Me switch?
