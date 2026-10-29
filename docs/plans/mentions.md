# Plan: mentions (@name in what people write)

Status: built on `feat/mentions` (2026-10-29): comments only, mentions drawn as chips, `@all`
for the whole crew. Stage 1 (backend) and stage 2 (frontend) each one commit. One change on
the way: the menu rows and the pick live in `useMentions` (`shared/ui`), the `MentionMenu` is
the rows alone, so the design page can show it still. Builds on `docs/plans/notifications.md` (news and push) and
`docs/plans/comments.md`.

## Goal

Anyone writing a comment can point at a crew member the Telegram way: type `@`, pick the
person (or everyone, `@all`), their name lands in the text. The mentioned person gets a line in
their news (and a push when they have it on) that opens the card where they were mentioned, and
the name shows as a small chip that opens their member page.

## Where text is written

| Place | Length | Shows on | Mentions |
|---|---|---|---|
| A comment or reply (`Composer`) | 500 | The card's page | Yes |
| A check-in note (`CheckInCard`) | 500 | The check-in's journal card | No (D3): a note is about my day, not a conversation |
| A proposal's title, rules, punishments | 60 / 500 / 80 | The challenge page | No (D3) |
| A display name, a crew name | 40 | Everywhere | No |

## What changes for members

| | Today | After |
|---|---|---|
| Writing a comment | Plain text | Typing `@` opens a short list: everyone (`@all`), then the crew's members, narrowed as I type; a tap puts `@Name ` in the text |
| Reading a comment | Plain text | `@Name` and `@all` are drawn as chips (a soft accent background, the app's radius); a tap on a name opens that member's page |
| Being mentioned | Nothing | A line in my news: "Ana mentioned you: ... @Ion ..."; a tap opens the card; a push with the same line |
| `@all` | - | Everyone who can see the card (but the writer) gets the same line |
| Mentioning someone who cannot see the card | - | The name shows, they are not told (D5) |

## Mechanism

### The text stays plain (D1)

A mention is the plain text `@` followed by a member's display name, as it is written: `@Ana`,
`@Ana Maria`. No markup, no ids in the text: what people typed is what is stored, copied and
searched. Both sides resolve mentions the same way, against the crew's members:

- `@all` first (D7: one spelling, shown translated in the menu), then names tried longest
  first, matched case-insensitively (display names are unique per crew, case-insensitively,
  `member_unique_display_name_per_crew`);
- the match must end at the end of the text or before a character that cannot continue a name
  (space, punctuation);
- `@` with no member behind it is left alone, as text.

Ceiling: a renamed member's old mentions stop being recognised (text is frozen, names are not).
Acceptable; if it ever matters, store the mentioned ids in the comment's or note's facts at write
time and resolve from them.

### Backend: one entry point, one more kind

- `apps/notifications/services.py`: `mention(*, actor, source, target, text)` finds the mentioned
  members (`apps/crews/mentions.py: find(text, crew_id) -> list[Member] | ALL`, the parser above;
  `@all` means every member of the crew), keeps the ones who may see `target`
  (`targets.of(target).visible(member)`), and calls `notify(kind=MENTION, recipients=...,
  facts={"text": snippet})`. The caller never parses.
- `Notification.Kind.MENTION = "mention"`. `texts.json`: `{actor} te-a mentionat: {text}` /
  `{actor} mentioned you: {text}` (Romanian with diacritics in the JSON, as today).
- Mention wins (D2): comments call `mention()` before `_tell()`. Notifications are unique per
  `(recipient, source)`, so a mentioned card owner reads "mentioned you", not "commented".
- Comments: `add()` calls `mention(actor=member, source=comment, target=found, text=comment.text)`.
  Delete already retracts every notification whose source is the comment.
- No new endpoints. `NotificationOut.kind` grows by `mention` (`make schema`).

### Frontend: one parser, one menu, one renderer

- `shared/lib/mentions.ts`: `findMentions(text, people)` -> segments
  `[{text} | {text, member} | {text, all: true}]` (the parser above, same rules);
  `mentionQuery(value, caret)` -> the word after an `@` under the caret, or null;
  `insertMention(value, caret, name)`.
- `shared/ui/MentionMenu.tsx`: a small list over the box ("Everyone" first, then avatar + name
  for members other than me, at most 5 rows), narrowed by the typed prefix; a tap inserts
  `@Name ` and puts the caret after it; Escape closes it. Driven by a hook
  `useMentions({ value, onChange, people, box })` that returns the menu and the caret watcher;
  it does not touch the textarea's own behaviour.
- `shared/ui/MentionText.tsx`: renders a text with its mentions as chips: `@Name` is a `Link` to
  `/crew/members/{id}`, `@all` a plain chip; both a soft accent background (`--color-accent-soft`),
  the small radius, no underline, inline with the text (design-system note added). Used by
  `CommentBubble` for its `text`; `Comments` already has the crew's members.
- Hooked up in `features/comments/components/Comments.tsx` (the `Composer`).
- News: `news.mention` = "mentioned you" (ro: "te-a mentionat"), the line shows the snippet like a
  comment's; the tap opens the card as today (`newsLink` follows `target`). Push: the same line.
- i18n keys: `mentions.everyone` ("Everyone" / "Toata lumea", the `@all` row), `news.mention`.

## Stages

1. **Backend**: parser, `mention()` service, kind + texts, the comments call, schema; tests for
   the parser (names with spaces, case, punctuation, unknown names, a name that is the prefix of
   another, `@all`), the service (visibility, dedupe with comment/reply, retract on delete),
   and the line texts.
2. **Frontend**: parser + tests, menu + hook, chip renderer, the comment composer, news line,
   i18n, design-system note; tests for typing `@` -> picking a name -> text, for a rendered chip
   and its link, and for the news line.

## Decisions (defaults; say which to change)

- D1: plain `@Display Name` in the text, resolved by name on both sides. No ids, no markup.
- D2: a mention outranks a comment or reply notification for the same person and source.
- D3: comments only (the owner's call: a check-in note is not a conversation). Proposal texts
  stay plain: everyone who can see the challenge already gets it, and a mention there has no
  one place to open.
- D4: the menu lists the crew's other members; mentioning yourself is text, nothing more.
- D5: someone who cannot see the card is not notified (the name still shows in the text).
- D6: the menu opens on `@` at the start or after a space, closes on space when nothing matches,
  and never changes what was typed on its own.
- D7: `@all` (one spelling, shown as "Everyone" in the menu) reaches everyone who can see the
  card, except the writer. It is a mention like the others: the same kind, the same line.
- D8: mentions are drawn as chips, not plain accent text (the owner's call).

## Out of scope

- Mentions in check-in notes and proposal texts, a mentions tab in the news, searching by
  mention, `@all` limited to admins.
