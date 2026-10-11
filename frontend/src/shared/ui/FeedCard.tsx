import type { ReactNode } from "react";
import { Link } from "react-router";

import { cx } from "@/shared/lib/cx";

import { Avatar, AvatarStack } from "./Avatar";
import { ChallengeChip } from "./ChallengeChip";
import styles from "./FeedCard.module.css";
import { Icon, type IconName } from "./Icon";
import { ProgressBar } from "./ProgressBar";
import { ProofMosaic, type FeedProof } from "./ProofMosaic";

type Person = { id: string; name: string; seed: string };

/**
 * One moment in the crew's journal, as a card of its own. The header says who (one avatar with
 * today's ring, or a stack for a group), what in one line, the challenge as a chip and when. The
 * body depends on the kind: proofs as a `ProofMosaic`, an amount ("+12 pages") with a bar to the
 * target, or a big number for a streak milestone; a plain check-in or a group has none. The
 * footer holds short facts ("7 days in a row") and, at its end, the `reactions`; last, `comments`:
 * a link to the card's thread with who wrote last and "3 comments" (or "Comment").
 * `tone="success"` marks a milestone or the whole crew finishing the day.
 */
export function FeedCard({
  person,
  people,
  ring,
  text,
  challenge,
  time,
  tone = "default",
  highlight,
  amount,
  proofs = [],
  onOpenProof,
  moreLabel,
  facts = [],
  reactions,
  comments,
}: {
  /** One member: an avatar. */
  person?: Person;
  /** Several members (a group of plain check-ins, the whole crew): a stack, named in `text`. */
  people?: { members: Person[]; label: string };
  /** The person's ring today. Say it in `text` or the facts too. */
  ring?: "done" | "todo";
  /** "Ana checked in", "Ana and Dan checked in Walk", "The whole crew finished the day". */
  text: string;
  challenge?: { icon: IconName; label: string };
  /** "5 min ago", "21:40", formatted by the caller. */
  time?: string;
  tone?: "default" | "success";
  /** A milestone's big number and its line ("7", "days in a row"), or the line alone. */
  highlight?: { value?: string; text: string };
  /** A quantity: "+12 pages", "20 today", and a bar when there is a target. */
  amount?: {
    value: string;
    detail?: string;
    progress?: { value: number; max: number; label: string };
  };
  proofs?: FeedProof[];
  onOpenProof?: (index: number) => void;
  /** Accessible name of "+N" on the mosaic. */
  moreLabel?: string;
  /** Short facts in the footer: "7 days in a row", "3 proofs". */
  facts?: ReactNode[];
  /** The reactions (chips and the react button), at the end of the footer row. */
  reactions?: ReactNode;
  /** Under the footer: a link to the card's comments, with its last writers ("3 comments") and,
   * when some are unread, a dot (`unread` says it to screen readers: "2 new"). */
  comments?: { to: string; text: string; people: Person[]; peopleLabel: string; unread?: string };
}) {
  const footer = facts.length > 0 || reactions;
  // One stage per card, the middle a reaction flies over: the photos when there are any.
  const stage = proofs.length > 0 ? undefined : "";
  return (
    <article className={cx(styles.card, tone === "success" && styles.success)}>
      <header className={styles.head}>
        {people ? (
          <AvatarStack members={people.members} label={people.label} />
        ) : (
          person && <Avatar name={person.name} seed={person.seed} ring={ring} />
        )}
        <div className={styles.who}>
          <p className={styles.text}>{text}</p>
          {(challenge || time) && (
            <p className={styles.meta}>
              {challenge && <ChallengeChip icon={challenge.icon} label={challenge.label} />}
              {time && <span className={styles.time}>{time}</span>}
            </p>
          )}
        </div>
      </header>
      {highlight && (
        <p className={styles.highlight} data-stage={stage}>
          {highlight.value && <span className={styles.big}>{highlight.value}</span>}
          <span>{highlight.text}</span>
        </p>
      )}
      {amount && (
        <div className={styles.amount} data-stage={stage}>
          <p className={styles.amountLine}>
            <span className={styles.amountValue}>{amount.value}</span>
            {amount.detail && <span className={styles.time}>{amount.detail}</span>}
          </p>
          {amount.progress && (
            <ProgressBar
              value={amount.progress.value}
              max={amount.progress.max}
              label={amount.progress.label}
            />
          )}
        </div>
      )}
      {proofs.length > 0 && (
        <ProofMosaic proofs={proofs} onOpen={onOpenProof} moreLabel={moreLabel} />
      )}
      {footer && (
        <footer className={styles.foot}>
          {reactions && <div className={styles.reactions}>{reactions}</div>}
          {facts.length > 0 && (
            <div className={styles.facts}>
              {facts.map((fact, i) => (
                <span key={i} className={styles.fact}>
                  {fact}
                </span>
              ))}
            </div>
          )}
        </footer>
      )}
      {comments && (
        <Link to={comments.to} className={styles.comments}>
          {comments.people.length > 0 ? (
            <AvatarStack members={comments.people} label={comments.peopleLabel} />
          ) : (
            <Icon name="messageCircle" size={20} />
          )}
          <span className={styles.commentsText}>
            {comments.text}
            {comments.unread && (
              <>
                <span className={styles.unread} aria-hidden="true" />
                <span className={styles.hidden}>{`, ${comments.unread}`}</span>
              </>
            )}
          </span>
          <Icon name="chevronRight" size={18} />
        </Link>
      )}
    </article>
  );
}
