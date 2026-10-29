import type { ComponentProps, ReactNode } from "react";

import { cx } from "@/shared/lib/cx";

import { Avatar, avatarColor } from "./Avatar";
import styles from "./CommentBubble.module.css";
import { Quote } from "./Quote";

/**
 * One message of a chat, as Telegram draws it. Others' are on the left: their name (in their
 * avatar color) on the first of a run, their avatar beside the last. Yours are on the right,
 * tinted, without either. Inside the bubble: the `quote` of what it answers, its `media` (photos,
 * a GIF) across the bubble, the text, then the `reactions` at the bottom left and the time at the bottom right. `actions` sit beside the
 * bubble; on a computer they show on hover. The whole message is an `article`, so holding it
 * opens its reactions' menu; `flash` lights it up once (a quote led here).
 */
export function CommentBubble({
  id,
  name,
  seed,
  time,
  text,
  mine = false,
  first = true,
  last = true,
  quote,
  media,
  reactions,
  actions,
  flash = false,
}: {
  /** The element's id, so a quote can lead to it. */
  id?: string;
  /** The writer: their name and avatar. */
  name: string;
  seed: string;
  /** "08:23", formatted by the caller. */
  time: string;
  /** The text, or it rendered with its mentions (`MentionText`). */
  text: ReactNode;
  mine?: boolean;
  /** The first of a run of one writer's messages: shows their name. */
  first?: boolean;
  /** The last of a run: shows their avatar and the bubble's tail. */
  last?: boolean;
  quote?: ComponentProps<typeof Quote>;
  /** Its photos or GIF (a `ProofMosaic`): the bubble then takes its widest. */
  media?: ReactNode;
  /** Its reactions' chips; an empty `[data-empty]` one takes no room. */
  reactions?: ReactNode;
  /** "Reply" and the react button, beside the bubble. */
  actions?: ReactNode;
  flash?: boolean;
}) {
  // An invisible copy of the time keeps the last line clear of the real one, in any language.
  const room = (
    <span className={styles.room} aria-hidden="true">
      {time}
    </span>
  );
  return (
    <article
      id={id}
      className={cx(
        styles.message,
        mine && styles.mine,
        first && styles.first,
        flash && styles.flash,
      )}
    >
      {!mine &&
        (last ? (
          <Avatar name={name} seed={seed} size="sm" />
        ) : (
          <span className={styles.gutter} aria-hidden="true" />
        ))}
      <div className={cx(styles.bubble, last && styles.tail, Boolean(media) && styles.withMedia)}>
        {!mine && first && (
          <p className={styles.name} data-color={avatarColor(seed)}>
            {name}
          </p>
        )}
        {quote && <Quote {...quote} />}
        {media}
        <p className={styles.text}>
          {text}
          {room}
        </p>
        {reactions && (
          <div className={styles.reactions}>
            {reactions}
            {room}
          </div>
        )}
        <span className={styles.time}>{time}</span>
      </div>
      {actions && <div className={styles.actions}>{actions}</div>}
    </article>
  );
}
