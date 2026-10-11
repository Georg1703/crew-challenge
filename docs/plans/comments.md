# Plan: comments on the crew's journal

Status: agreed (2026-10-10); stages 1 to 4 built; photos and GIFs (stages 5 and 6) agreed 2026-10-11, stage 5 built. Four stages after the plan, on one branch
(`feat/comments`), one commit per stage, each committed after the owner's review.
Each stage works on its own and with the release before it still serving.

Design: variant C of the "Comments designs" canvas
(https://claude.ai/artifact/21HUX8FPpoGdy45FQLPURc): the feed card says who commented and how
many; tapping it opens the card's own page with the comments under it, drawn like Telegram
(row T of the canvas, 2026-10-11).

Priorities, in order: a new comment reaches the people looking at the card within seconds;
members notice comments meant for them without hunting; comments attach to anything registered
(journal cards now); no new server parts; a journal page costs the same with or without comments.

## Goal

Every card in the crew's journal (`JournalEntry`: a check-in post, a spin drawn or served, the
crew's finished day) can be commented on, every comment can be answered and
reacted to. The feed shows each card's comment count, who wrote last and a dot when something
is unread; the Crew tab shows a badge for new comments meant for you.

## What changes for members

| | Today | After |
|---|---|---|
| Feed card footer | Reaction chips and a react button | Reaction chips; the react button on computers only (on a phone, hold the card); a comments line: the last writers' avatars, "3 comments", a dot when unread |
| Talking about a post | Not possible in the app | Tap the comments line (or "Comment"): the card's page with its thread and a box to write |
| Answering or reacting to a comment | - | Phone: hold the comment, then an emoji, "Reply", "Copy text" or "Delete". Computer: Reply and the react button beside it, on hover |
| Fixing a typo | - | Delete your comment within a minute, if nobody has replied, and write it again |
| Knowing someone answered you | - | A badge on the Crew tab, a dot on the card |

## Decisions

Agreed (2026-10-10):
- Variant C: the card's own page.
- The react button shows on computers only (a mouse or trackpad); on phones and tablets members
  hold the card to react, as today.
- A card's page asks for new comments every 5 s while it is visible; nothing new on the server.
- Unread marks: the server remembers what each member has read on each card; a dot on cards
  with unread comments, a badge on the Crew tab for comments on your cards and on cards you
  commented on.
- Comments are generic: they attach to any registered target, like reactions. Journal cards
  are the only target now.
- Any comment can be answered, however long the chain; the reply quotes it (2026-10-11: the
  5-level limit was there for the indented thread and went with it).
- Deleting: only the writer, only within 1 minute of writing, only while it has no replies.
  Comments are soft deleted: the comment leaves the thread, the row stays (the admin can
  restore it).
- On a phone, holding a comment opens its menu: the quick emojis, "Reply" and, when allowed,
  "Delete". Comments take reactions like cards (one per person).
- Text up to 500 characters; no editing (delete within the minute and write again).

- The page is a chat like Telegram (2026-10-11, replacing an indented thread): one flat list,
  oldest first; a reply shows a quote of what it answers (tap it to go there); each writer's run
  together, name on the first, avatar beside the last; yours on the right in clay-soft;
  reactions inside the bubble at the bottom left, the time at the bottom right; a day pill when
  the day changes. The card stays pinned as a line under the bar once it scrolls away; scrolled
  up when new comments come, a button says how many. The menu adds "Copy text" (holding a
  comment selects no text on a phone).

With a proposed default (confirm or change):
1. **On a computer**, Reply and the react button show beside a comment under the pointer; the
   react button opens the same menu as a hold.
2. **Undoing a post someone else commented on is refused** (`409 post_has_comments`). Today an
   undo deletes the card with its reactions; deleting others' words silently is worse. Not
   checked: the crew's day card an undo removes when the day is no longer finished (its
   comments go with it; it needs a commented crew card and an undo after it, the same day).
3. **The card's page is full screen** (no tab bar), like the proposal form: the composer sits
   at the bottom.
4. **Sending waits for the server** (about 0.2 s): the send button shows it at once, the
   comment appears with the answer, the box empties; on an error the text stays. No
   optimistic insert: a comment with a temporary id would race the 5 s refresh and need a
   rollback.
5. **New members** see older comments as read: what was said before they joined never counts
   as unread.

## How new comments reach people

| Where the reader is | How it arrives | Delay | Cost |
|---|---|---|---|
| On the card's page | `GET` the thread every 5 s while visible (TanStack `refetchInterval`; stops in the background) | up to 5 s | 1 request / 5 s per open page, 5 small indexed queries |
| In the feed | The journal refresh (every 60 s, on focus, after a post) brings each card's count, last writers and unread | up to 60 s | 2 queries per journal page, whatever its size |
| Anywhere in the app | The Crew tab badge: `GET /comments/unread` every 60 s and on focus; opening a card clears it | up to 60 s | 1 query a minute per open app |
| App closed | Nothing now. Web Push is after v1; when it comes, each comment row is the outbox: an `on_commit` task notifies the card's owner and the replied-to writer | - | - |

Why not a live stream now: gunicorn runs 3 sync workers, each serving one request at a time;
an open SSE connection would hold a worker, so three open cards would stall the site. A stream
needs Django on ASGI (uvicorn, a new dependency), Redis pub/sub and reconnects when an iPhone
brings the app back. For a crew of a few people, 5 s polling gets the same feel with none of it.
Upgrade path when crews grow: first an ETag on the thread (a `304` from one aggregate query),
then SSE on ASGI that only says "card X changed" while the same `GET` stays the source of truth.

## Model

New app `apps/comments`, generic like `apps/reactions`:

```
Comment(CrewScopedSoftDeleteModel)     # id, crew, created_at, updated_at, deleted_at
  target_type, target_id               # generic key: the commented thing (a card now)
  member    FK Member, cascade         # the writer
  parent    FK Comment, null, cascade  # the comment it answers, on the same target
  text      up to 500 characters
  reactions GenericRelation(Reaction)  # comments are a reaction target
  index (target_type, target_id, created_at)

CommentRead(CrewScopedModel)           # stage 4
  member FK Member, cascade
  target_type, target_id
  read_at                              # when this member last saw the thread
  unique (member, target_type, target_id)
```

- The target registry moves from `apps/reactions/targets.py` to `apps/crews/targets.py`, shared
  by reactions and comments. `Target(key, model, visible, owner=None, comments=False)`:
  `visible(member)` is the queryset of targets the member may see (replaces `find`: one
  callable answers "this one?" and "which ones?"); `owner` names the member field of whoever
  made it (for the badge, added in stage 4); `comments` says whether it takes comments.
- Registered: `entry` (the journal: `owner="member"`, `comments=True`) and `comment` (the
  comments app itself: reactions only; replies are how comments answer comments).
- `JournalEntry` declares `comments = GenericRelation(...)`, so deleting a card deletes its
  comments (and their reactions), as with reactions today.
- Read marks of a deleted card stay behind (a few bytes each; a sweep if ever needed).

## API

```
GET    /api/v1/comments/{target}/{id}          the whole thread, oldest first: [{id, member_id,
                                               parent_id, text, created_at, reactions}]
POST   /api/v1/comments/{target}/{id}          {text, parent_id?} -> 201 the comment
DELETE /api/v1/comments/{comment_id}           yours, within a minute, without replies -> 204
PUT    /api/v1/comments/{target}/{id}/read     marks the thread read up to now -> 204 (stage 4)
GET    /api/v1/comments/unread                 {count}: unread comments for the Crew badge (stage 4)
PUT    /api/v1/reactions/comment/{id}          react to a comment (the existing endpoint, a new target)
GET    /api/v1/journal/{id}                    one card, as in the journal (the card's page)
GET    /api/v1/journal                         each card gains `comments`: {count, member_ids
                                               (last 3 writers), unread (stage 4)}
```

- No cursor on a thread: threads are short. Add one if a thread passes a few hundred.
- New error codes: `comment_not_found`, `card_not_found` (404), `not_your_comment` (403),
  `comment_has_replies`, `comment_too_old`, `post_has_comments` (409).
- Names and avatars come from the crew's members, as for reactions; the thread carries ids only.

## Rules in services

- `add(member, target, id, text, parent_id)`: the target takes comments and is visible to the
  member; the text is trimmed, 1 to 500 characters; a parent must be on the same target; the
  parent row is locked (`select_for_update`) so a reply and a delete never
  cross.
- `delete(member, comment_id)`: the writer only; `clock.now()` within 1 minute of
  `created_at`; no replies that are not deleted; the row is locked; soft.
- `undo_last` (check-ins): refused when the post's card has comments by someone else.
- Unread for a member on a target: comments by others newer than their read mark, and never
  older than when they joined the crew.
- The badge: unread comments on visible targets that the member made (`owner`) or commented on.

## Stages

| Stage | What works at the end | Size |
|---|---|---|
| 0. Plan | This plan | S |
| 1. React button on computers only | Phones and tablets show chips only; holding a card opens the quick row | S |
| 2. Comments API | Comments can be written, read, answered, reacted to and deleted over the API; cards carry their count | M |
| 3. The card's page | Members comment, reply and react in the app; new comments show within 5 s | L |
| 4. Unread | Dots on cards, the Crew tab badge, read marks | M |

Stage 2 is invisible to members and can ship alone; 3 needs 2; 4 needs 3. Stage 1 stands alone.

### Stage 1 - React button on computers only

- `reactions.module.css`: under `@media (hover: none), (pointer: coarse)` the react button is
  visually hidden but stays in the page: screen readers still find it, and it stays the menu's
  anchor when a hold opens it. Comments reuse the same rule in stage 3.
- e2e: on a touch profile the button is not visible and holding a card opens the quick row; on
  desktop the button opens it.

### Stage 2 - Comments API

- The shared registry (`apps/crews/targets.py`), with reactions moved onto it;
  `journal.selectors.reactable` becomes `visible`.
- `apps/comments`: models, migration, services (`add`, `delete`), selectors (`thread`,
  `summaries` for a page of cards: count and last 3 writers in one query), API (the thread
  carries each comment's reactions: one more query), admin (unrestricted, `all_objects`), the
  `comment` reaction target.
- Journal: `comments` on every card in `GET /journal` (the "fuller page costs no more queries"
  test covers it), `GET /journal/{id}`.
- Check-ins: the undo rule.
- import-linter: comments know their targets only through the registry.
- Tests: a chain of replies; delete at 59 s and at 61 s (time-machine), with a
  reply, with a deleted reply, someone else's; a deleted comment leaves the thread and the
  counts; a reply racing a delete; a hidden card (left challenge, deleted challenge, another
  crew) -> 404; a reaction on a comment, and on a hidden one -> 404; undo refused with others'
  comments, allowed with only your own; deleting a card deletes its comments.
- Docs: `api-conventions.md` (endpoints, codes), `backend.md` (the registry), glossary
  (Comment, Reply), AGENTS.md (comments join the v1 list: seven things).

### Stage 3 - The card's page

- `shared/ui` (each with all its states on `/design` and in `design-system.md`):
  - `ReactionMenu`: `actions` (rows under the emojis: "Reply", "Delete", "Who reacted"); the
    separate "Who reacted" props become one of them.
  - `Composer`: a growing text box (up to about 5 lines, native `maxlength` 500), the send
    button with its sending state, and when replying the `Quote` of what it answers with a stop
    button.
  - `CommentBubble`: a chat message (see Decisions), with its `Quote`, its reactions inside and
    its actions beside it; `Quote`: what a message answers.
  - `FeedCard`: `comments`, a last row linking to the card's page (last writers, "3 comments").
  - `Screen`: at least as tall as the screen, so the composer sits at the bottom of a short page.
- Reactions: `actions` rows for the menu; `useReactions` gives the chips and the button apart (a
  message puts its chips in the bubble and its button beside it); the menu is placed inside the
  screen wherever its button is. A hold on the message (its own `article`) opens it, as on cards.
- Check-ins: the card drawing moves out of `CrewFeed` into `JournalCard`, used by the feed and
  the card's page; route `/crew/cards/:id` (full screen): a bar with back and the count (the
  card pinned in it as a `Quote` once scrolled away), the card, the chat, the composer; loading,
  empty ("No comments yet") and not found states.
- `features/comments`: `useThread` (5 s while visible), `useAddComment`, `useDeleteComment`,
  `Comments` (the chat: runs, day pills, quotes that lead to what they answer, "3 new" while
  scrolled up, following the newest at the end).
- "Delete" is offered when the menu opens: your comment, no replies, under a minute old. No
  timers; the server decides at the edge.
- i18n: en and ro.
- Tests: Vitest for a writer's name once per run, a quote leading to its message, Reply and
  Copy text on every comment, Delete offered only when allowed, sending a reply and an error keeping
  the text. e2e: Ana comments, Bogdan's open page shows it within
  5 s, he holds it and replies, reacts to it; Ana deletes hers within the minute, and cannot
  once replied.
- Check on a real iPhone and Android phone: the composer stays above the keyboard; holding a
  comment does not select its text.

### Stage 4 - Unread

- `CommentRead`, `PUT .../read`, `GET /comments/unread`; `unread` in the journal's `comments`.
- The card's page marks the thread read when it opens and whenever a refresh brings something
  new; that clears the card's dot in the cached journal and refreshes the badge.
- `shared/ui` `TabBar`: a badge on a tab (a number, "9+" above nine), on `/design`.
- Tests: unread for others' comments only; deleted ones never count; joined later; the badge
  counts your cards and cards you commented on and ignores hidden ones; the read mark clears
  both.

### Stage 5 - Photos and GIFs in comments: the API

Agreed (2026-10-11): a comment carries photos and GIFs (no videos), up to 5, and its text may be
empty when it has one. Phones offer GIFs through the gallery and some keyboards, but a plain text
box takes none: they come in as files, with no outside GIF service.

- The files are proofs (`apps/proofs`, generic): their subject is the commented target (the
  card), each member's drafts there are theirs alone (`drafts`, `uploaded_drafts` and `publish`
  take a `member`; the 5 of a post to come count per member), and sending the comment publishes
  them with `post_id` = the comment.
- `POST /api/v1/comments/{target}/{id}/images` (the same body as a check-in's proof, a photo
  only) -> 201 the draft file and how to send it; then the generic `/proofs/{id}/complete` and
  `DELETE /proofs/{id}`. A draft never sent goes after a day (`expire_proofs`).
- The thread gives each comment its `proofs`, and `drafts`: mine on this target.
- `add`: refused while one of my drafts uploads (`uploads_running`); empty text needs an
  uploaded photo; the photos join the comment.
- GIFs: `image/gif` is a photo type (check-ins take them too).
- A card that goes (an undo, the crew's day undone) takes its comments' photos, files included.
- import-linter: comments may use proofs (a generic block), still never challenges, check-ins or
  the journal.

### Stage 6 - Photos and GIFs in comments: the app

- The box gets an image button (photos and GIFs only) and takes pasted images (a computer, or a
  keyboard that copies a GIF); the picked files show as tiles above the box while they upload
  (`ProofTiles`), and Send waits for them, as a check-in does.
- GIFs are sent as they are (shrinking a GIF to a JPEG would stop it), with a first-frame
  thumbnail.
- The bubble shows the photos at its top (one at full width, several as a mosaic), the text
  under them; a tap opens the viewer. A quote of a comment with no text says "Photo".
- Tests: picking, pasting, Send waiting for an upload, a GIF kept as it is, the bubble's photos.

## Edge cases

| Case | Behaviour |
|---|---|
| Replying to a comment deleted meanwhile | `404 comment_not_found`; the text stays in the box, the reply's quote goes, a toast says why |
| Deleting at the minute's edge | The server decides; after it, `409 comment_too_old` |
| A reply and a delete at the same moment | Row locks: either the reply lands and the delete is refused, or the delete wins and the reply gets 404 |
| Deleting a reply, then its parent | Allowed within the parent's minute: deleted replies do not count |
| An admin deletes a comment that was answered | Its replies stay in the chat, without their quote; restoring it brings the quotes back |
| Writing on a card that was just undone | `404 target_not_found`; the page shows the not found state |
| Undoing a post others commented on | Refused (`post_has_comments`); with only your own comments it goes, with them |
| Leaving a challenge | Its cards disappear for you, with their threads; your comments stay for the others |
| A deleted challenge | Its cards and comments are hidden; they never count as unread |
| Commenting on your own card | Allowed; your own comments are never unread for you |
| Reacting to your own comment | Allowed, as on cards |
| Empty or spaces only | Send stays unavailable; the API answers `400 validation_failed` (also over 500) |
| A double tap on send | The button waits for the first send |
| Offline when sending | The text stays, a toast |
| The app goes to the background | Refreshing stops; it refreshes when the app comes back |
| A member deleted in the admin | Their comments go, with the replies under them (admin only) |

## Risks

| Risk | Answer |
|---|---|
| The keyboard covers the composer on iPhone | `100dvh` page with the composer at its bottom; checked on a real iPhone in stage 3; `visualViewport` offset if needed |
| A hold on a comment selects its text (iOS) | `user-select: none` and `-webkit-touch-callout: none` on the bubble, as `HoldButton` has; copying a comment's text is then not possible (a "Copy" action is easy to add); checked on a real iPhone |
| Polling load | 5 small queries per open page every 5 s; measured in stage 3; the ETag, then SSE, is the path if it ever matters |
| Members miss the hold on phones | It already works on cards; a one-time hint is easy to add later |
| Scope | v1 lists six things: comments become the seventh (AGENTS.md and the glossary change in stage 2) |

## Out of scope

Web Push and any notification outside the app (after v1), mentions, editing, photos or links
in comments, "typing...", "seen by", a rate limit (add one if a client ever loops).
