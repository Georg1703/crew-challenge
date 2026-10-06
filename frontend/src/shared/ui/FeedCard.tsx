import type { ReactNode } from "react";

import { cx } from "@/shared/lib/cx";

import { Avatar, AvatarStack } from "./Avatar";
import { ChallengeChip } from "./ChallengeChip";
import type { DayState } from "./DayMark";
import styles from "./FeedCard.module.css";
import type { IconName } from "./Icon";
import { MiniWeek } from "./MiniWeek";
import { ProgressBar } from "./ProgressBar";
import { ProofMosaic, type FeedProof } from "./ProofMosaic";

type Person = { id: string; name: string; seed: string };

/**
 * One moment in the crew's journal, as a card of its own. The header says who (one avatar with
 * today's ring, or a stack for a group), what in one line, the challenge as a chip and when. The
 * body depends on the kind: proofs as a `ProofMosaic`, an amount ("+12 pages") with a bar to the
 * target, or a big number for a streak milestone; a plain check-in or a group has none. The
 * footer holds the last seven days (`MiniWeek`) and short facts ("7 days in a row", "day 5 of
 * 30"). `tone="success"` marks a milestone or the whole crew finishing the day.
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
  week,
  facts = [],
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
  /** A milestone's big number and its line: "7", "days in a row". */
  highlight?: { value: string; text: string };
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
  week?: { days: { key: string; state: DayState; today?: boolean }[]; label: string };
  /** Short facts in the footer: "7 days in a row", "day 5 of 30", "3 proofs". */
  facts?: ReactNode[];
}) {
  const footer = week || facts.length > 0;
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
        <p className={styles.highlight}>
          <span className={styles.big}>{highlight.value}</span>
          <span>{highlight.text}</span>
        </p>
      )}
      {amount && (
        <div className={styles.amount}>
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
          {week && <MiniWeek days={week.days} label={week.label} />}
          {facts.map((fact, i) => (
            <span key={i} className={styles.fact}>
              {fact}
            </span>
          ))}
        </footer>
      )}
    </article>
  );
}
