import { useEffect, useMemo, useRef, useState, type ComponentProps } from "react";
import { useTranslation } from "react-i18next";

import { isApiError, type Member } from "@/api";
import { useMe } from "@/features/auth";
import {
  ProofTiles,
  SHOWN_PROOFS,
  shownTile,
  useDrafts,
  useProofUpload,
  viewerItem,
} from "@/features/proofs";
import { pickerTexts, useReactions, type ReactionSummary } from "@/features/reactions";
import { errorMessage } from "@/i18n/errors";
import { addDays } from "@/shared/lib/dates";
import { formatDayLong, formatTime, todayIn } from "@/shared/lib/format";
import { useReducedMotion } from "@/shared/motion";
import {
  Banner,
  Button,
  CommentBubble,
  Composer,
  EmojiPicker,
  Icon,
  ProofMosaic,
  ProofViewer,
  Sheet,
  Skeleton,
  StatusPill,
  useToast,
  type MenuAction,
  type ViewerItem,
} from "@/shared/ui";

import {
  commentSubject,
  MAX_LENGTH,
  useAddComment,
  useDeleteComment,
  useMarkRead,
  usePatchCommentReactions,
  useThread,
  type Comment,
  type CommentTarget,
} from "../api";
import styles from "../comments.module.css";
import { deletable } from "../thread";

const FLASH_MS = 1_000;

/**
 * A target's comments as a chat, like Telegram: oldest first, each writer's run of messages
 * together, a reply showing a quote of what it answers (tap it to go there), reactions inside the
 * bubbles, photos and GIFs at the top of theirs, new ones every 5 s and the message box docked
 * at the bottom (emojis of its own; photos picked or pasted upload as tiles over it, and sending
 * waits for them; a photo alone is a whole message). On a phone, holding a
 * message opens its menu: the quick emojis, "Reply", "Copy text" and, in its
 * first minute while nobody has replied, "Delete". On a computer Reply and the react button show
 * beside a message under the pointer. At the end of the chat new messages come into view; above
 * it a button says how many came and leads down to them.
 */
export function Comments({
  target,
  id,
  people,
  timeZone,
  onRead,
}: {
  target: CommentTarget;
  id: string;
  /** The crew's members: names and avatars for the ids in the chat. */
  people: Member[];
  timeZone: string;
  /** The chat was marked read (the owner clears its unread mark). */
  onRead?: () => void;
}) {
  const { t, i18n } = useTranslation();
  const language = i18n.language;
  const toast = useToast();
  const still = useReducedMotion();
  const me = useMe().data?.member?.id;
  const thread = useThread(target, id);
  const add = useAddComment(target, id);
  const remove = useDeleteComment(target, id);
  const patchReactions = usePatchCommentReactions(target, id);
  const [text, setText] = useState("");
  const [replyTo, setReplyTo] = useState<Comment | null>(null);
  const [flash, setFlash] = useState<string | null>(null);
  const [emojis, setEmojis] = useState(false);
  const [viewing, setViewing] = useState<{ items: ViewerItem[]; index: number } | null>(null);
  const box = useRef<HTMLTextAreaElement>(null);
  const subject = useMemo(() => commentSubject(target, id), [target, id]);
  const drafts = thread.data?.drafts ?? [];
  const { uploading, ready } = useDrafts(subject.key, drafts);
  const pick = useProofUpload(subject, () => thread.refetch());
  const texts = useMemo(() => pickerTexts(t), [t]);
  const byId = useMemo(() => new Map(people.map((m) => [m.id, m])), [people]);
  const behavior: ScrollBehavior = still ? "auto" : "smooth";

  const list = thread.data?.results ?? [];
  const { end, fresh, toEnd } = useNewest(list, me, behavior);
  useReadMark(target, id, thread.data?.results, onRead);
  const byComment = new Map(list.map((c) => [c.id, c]));
  const answered = new Set(list.map((c) => c.parent_id));
  const writer = (memberId: string) => ({
    name: memberId === me ? t("comments.you") : (byId.get(memberId)?.display_name ?? "?"),
    seed: byId.get(memberId)?.avatar_seed ?? memberId,
  });

  const reply = (comment: Comment) => {
    setReplyTo(comment);
    box.current?.focus();
  };
  /** An emoji where the cursor is (or over what is selected), the cursor after it. */
  const insert = (emoji: string) => {
    setEmojis(false);
    const field = box.current;
    const start = field?.selectionStart ?? text.length;
    const stop = field?.selectionEnd ?? text.length;
    const next = text.slice(0, start) + emoji + text.slice(stop);
    if (next.length > MAX_LENGTH) return;
    setText(next);
    window.requestAnimationFrame(() => {
      field?.focus();
      field?.setSelectionRange(start + emoji.length, start + emoji.length);
    });
  };
  const goTo = (commentId: string) => {
    document.getElementById(anchorOf(commentId))?.scrollIntoView({ block: "center", behavior });
    setFlash(commentId);
    window.setTimeout(() => setFlash(null), FLASH_MS);
  };
  const send = () =>
    add.mutate(
      { text: text.trim(), ...(replyTo ? { parent_id: replyTo.id } : {}) },
      {
        onSuccess: () => {
          setText("");
          setReplyTo(null);
          toEnd();
        },
        onError: (error) => {
          toast(errorMessage(t, error), "error"); // the text stays, to send again
          if (isApiError(error) && error.code === "comment_not_found") setReplyTo(null);
        },
      },
    );
  /** A message's menu rows, worked out when it opens. */
  const menuOf = (comment: Comment) => (): MenuAction[] => [
    { label: t("comments.reply"), icon: "reply", onSelect: () => reply(comment) },
    ...(comment.text
      ? [
          {
            label: t("comments.copy"),
            icon: "copy",
            onSelect: () =>
              void navigator.clipboard
                .writeText(comment.text)
                .then(() => toast(t("comments.copied"))),
          } as const,
        ]
      : []),
    ...(deletable(comment, answered.has(comment.id), me)
      ? [
          {
            label: t("comments.delete"),
            icon: "trash",
            danger: true,
            onSelect: () =>
              remove.mutate(comment.id, {
                onError: (error) => toast(errorMessage(t, error), "error"),
              }),
          } as const,
        ]
      : []),
  ];

  const today = todayIn(timeZone);
  const dayOf = (comment: Comment) => todayIn(timeZone, new Date(comment.created_at));
  const dayLabel = (day: string) =>
    day === today
      ? t("crew.journal.today")
      : day === addDays(today, -1)
        ? t("crew.journal.yesterday")
        : formatDayLong(day, language);

  return (
    <section className={styles.comments} aria-label={t("comments.label")}>
      {thread.isPending && <Skeleton lines={3} />}
      {thread.isError && <Banner tone="danger" title={errorMessage(t, thread.error)} />}
      {thread.data && list.length === 0 && <p className={styles.empty}>{t("comments.empty")}</p>}
      {list.length > 0 && (
        <ul className={styles.chat}>
          {list.map((comment, i) => {
            const before = list[i - 1];
            const after = list[i + 1];
            const day = dayOf(comment);
            const newDay = !before || dayOf(before) !== day;
            const parent = comment.parent_id ? byComment.get(comment.parent_id) : undefined;
            const quoted = parent && writer(parent.member_id);
            const who = writer(comment.member_id);
            return (
              <li key={comment.id}>
                {newDay && (
                  <p className={styles.day}>
                    <StatusPill>{dayLabel(day)}</StatusPill>
                  </p>
                )}
                <Message
                  comment={comment}
                  {...who}
                  people={people}
                  mine={comment.member_id === me}
                  first={newDay || before.member_id !== comment.member_id}
                  last={!after || after.member_id !== comment.member_id || dayOf(after) !== day}
                  time={formatTime(comment.created_at, language, timeZone)}
                  quote={
                    parent &&
                    quoted && {
                      ...quoted,
                      text: parent.text || t("comments.photo"),
                      onClick: () => goTo(parent.id),
                      label: t("comments.goTo", { name: quoted.name }),
                    }
                  }
                  media={
                    comment.proofs.length > 0 && (
                      <ProofMosaic
                        proofs={comment.proofs.map((p) => shownTile(p, t, who.name))}
                        onOpen={(index) =>
                          setViewing({
                            items: comment.proofs.map((p) => viewerItem(p, who.name)),
                            index,
                          })
                        }
                        moreLabel={t("feed.more", { count: comment.proofs.length - SHOWN_PROOFS })}
                      />
                    )
                  }
                  flash={flash === comment.id}
                  menu={menuOf(comment)}
                  onReply={() => reply(comment)}
                  onReactions={(summary) => patchReactions(comment.id, summary)}
                />
              </li>
            );
          })}
        </ul>
      )}
      <div ref={end} className={styles.end} />
      <div className={styles.dock}>
        {fresh > 0 && (
          <Button
            variant="secondary"
            className={styles.jump}
            icon={<Icon name="chevronDown" size={20} />}
            onClick={toEnd}
          >
            {t("comments.fresh", { count: fresh })}
          </Button>
        )}
        <Composer
          ref={box}
          value={text}
          onChange={setText}
          onSend={send}
          label={t("comments.box")}
          placeholder={t(replyTo ? "comments.writeReply" : "comments.write")}
          sendLabel={t("comments.send")}
          sending={add.isPending}
          maxLength={MAX_LENGTH}
          replying={
            replyTo
              ? {
                  ...writer(replyTo.member_id),
                  text: replyTo.text,
                  stopLabel: t("comments.stopReplying"),
                  onStop: () => setReplyTo(null),
                }
              : undefined
          }
          onEmoji={() => setEmojis(true)}
          emojiLabel={t("comments.emoji")}
          onFiles={(files) => files.forEach(pick)}
          filesLabel={t("comments.addPhoto")}
          attached={ready}
          waiting={uploading}
          above={
            (drafts.length > 0 || uploading) && (
              <ProofTiles
                subject={subject}
                title={t("comments.yourPhotos")}
                proofs={drafts}
                onChanged={() => thread.refetch()}
                add={false}
              />
            )
          }
        />
      </div>
      <Sheet
        open={emojis}
        onClose={() => setEmojis(false)}
        title={t("comments.emoji")}
        closeLabel={t("common.close")}
      >
        <EmojiPicker
          texts={texts}
          errorText={t("reactions.pickerFailed")}
          retryLabel={t("common.retry")}
          onPick={insert}
        />
      </Sheet>
      <ProofViewer
        items={viewing?.items ?? []}
        index={viewing?.index ?? 0}
        onIndexChange={(index) => setViewing((v) => v && { ...v, index })}
        open={viewing !== null}
        onClose={() => setViewing(null)}
        label={t("proofs.viewer.label")}
        closeLabel={t("common.close")}
        previousLabel={t("proofs.viewer.previous")}
        nextLabel={t("proofs.viewer.next")}
      />
    </section>
  );
}

const anchorOf = (commentId: string) => `comment-${commentId}`;

/** One message with its reactions: the chips in the bubble, Reply and react beside it. */
function Message({
  comment,
  name,
  seed,
  people,
  mine,
  first,
  last,
  time,
  quote,
  media,
  flash,
  menu,
  onReply,
  onReactions,
}: {
  comment: Comment;
  name: string;
  seed: string;
  people: Member[];
  mine: boolean;
  first: boolean;
  last: boolean;
  time: string;
  quote: ComponentProps<typeof CommentBubble>["quote"];
  media: ComponentProps<typeof CommentBubble>["media"];
  flash: boolean;
  menu: () => MenuAction[];
  onReply: () => void;
  onReactions: (summary: ReactionSummary) => void;
}) {
  const { t } = useTranslation();
  const { chips, button } = useReactions({
    target: "comment",
    id: comment.id,
    summary: comment.reactions,
    people,
    onChange: onReactions,
    actions: menu,
  });
  return (
    <CommentBubble
      id={anchorOf(comment.id)}
      name={name}
      seed={seed}
      time={time}
      text={comment.text}
      mine={mine}
      first={first}
      last={last}
      quote={quote}
      media={media}
      flash={flash}
      reactions={chips}
      actions={
        <>
          <Button
            variant="ghost"
            className={styles.reply}
            icon={<Icon name="reply" size={18} />}
            aria-label={t("comments.reply")}
            onClick={onReply}
          />
          {button}
        </>
      }
    />
  );
}

/**
 * Following the newest message: while the end of the chat is in view, new ones are scrolled to;
 * above it, `fresh` counts the others' messages that came since, until the end is seen again.
 */
function useNewest(list: Comment[], me: string | undefined, behavior: ScrollBehavior) {
  const end = useRef<HTMLDivElement>(null);
  const [atEnd, setAtEnd] = useState(false);
  const [seenUntil, setSeenUntil] = useState<string | null>(null);
  const latest = list.at(-1)?.created_at ?? "";
  // Everything there when the chat opens, and whatever comes while the end is in view, is seen.
  if (list.length > 0 && (seenUntil === null || (atEnd && latest > seenUntil))) {
    setSeenUntil(latest);
  }
  useEffect(() => {
    const node = end.current;
    if (!node) return;
    // The docked message box covers the bottom of the screen: the end shows above it.
    const watch = new IntersectionObserver(([entry]) => setAtEnd(entry?.isIntersecting ?? false), {
      rootMargin: "0px 0px -120px 0px",
    });
    watch.observe(node);
    return () => watch.disconnect();
  }, []);
  const toEnd = () =>
    window.requestAnimationFrame(() =>
      window.scrollTo({ top: document.documentElement.scrollHeight, behavior }),
    );
  // A new message while at the end: bring it into view (only then, not on reaching the end).
  const followed = useRef(latest);
  useEffect(() => {
    if (latest === followed.current) return;
    followed.current = latest;
    if (atEnd) window.scrollTo({ top: document.documentElement.scrollHeight, behavior });
  }, [latest, atEnd, behavior]);
  const fresh =
    atEnd || seenUntil === null
      ? 0
      : list.filter((c) => c.created_at > seenUntil && c.member_id !== me).length;
  return { end, fresh, toEnd };
}

/** Seen: the chat is marked read when it opens and whenever a refresh brings something new. */
function useReadMark(
  target: CommentTarget,
  id: string,
  list: Comment[] | undefined,
  onRead: (() => void) | undefined,
) {
  const { mutate: markRead } = useMarkRead(target, id);
  const marked = useRef<string | null>(null);
  const latest = list ? (list.at(-1)?.created_at ?? "") : null;
  useEffect(() => {
    if (latest === null || latest === marked.current) return;
    marked.current = latest;
    markRead(undefined, { onSuccess: () => onRead?.() });
  }, [latest, markRead, onRead]);
}
