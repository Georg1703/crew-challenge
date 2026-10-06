import { Link } from "react-router";

import { cx } from "@/shared/lib/cx";

import { avatarColor, initials } from "./Avatar";
import styles from "./StoryAvatar.module.css";

/** One challenge due today: checked in, started (a number below the target), or still to do. */
export type StorySegment = "done" | "started" | "todo";

const R = 31; // circle radius in a 68 x 68 view box
const LENGTH = 2 * Math.PI * R;
const GAP = 7; // between segments, along the circle

/**
 * A member with today's ring split into one segment per challenge due today (none: a plain grey
 * ring), their name and a short line under it ("2/2"), and an optional count of proofs you have
 * not seen yet. Say all of it in `label`; with `to` it is a link to the member's page.
 */
export function StoryAvatar({
  name,
  seed,
  segments,
  size = "md",
  title,
  subtitle,
  complete = false,
  fresh = 0,
  label,
  to,
}: {
  name: string;
  seed: string;
  segments: StorySegment[];
  size?: "md" | "lg";
  /** Shown under the avatar ("Tu", "Ana"); leave out for none. */
  title?: string;
  /** Shown under the title ("2/2", "-"). */
  subtitle?: string;
  /** Everything due today is done: the subtitle turns success green. */
  complete?: boolean;
  /** New proofs since you last looked; 0 hides the count. */
  fresh?: number;
  label: string;
  to?: string;
}) {
  const part = segments.length > 0 ? LENGTH / segments.length : LENGTH;
  const gap = segments.length > 1 ? GAP : 0;
  const body = (
    <>
      <span className={cx(styles.face, styles[size])}>
        <svg className={styles.ring} viewBox="0 0 68 68" aria-hidden="true">
          {segments.length === 0 ? (
            <circle cx="34" cy="34" r={R} className={styles.none} />
          ) : (
            segments.map((segment, i) => (
              <circle
                key={i}
                cx="34"
                cy="34"
                r={R}
                className={styles[segment]}
                strokeDasharray={`${part - gap} ${LENGTH - part + gap}`}
                strokeDashoffset={-i * part}
              />
            ))
          )}
        </svg>
        <span className={styles.avatar} data-color={avatarColor(seed)}>
          {initials(name)}
        </span>
        {fresh > 0 && <span className={styles.fresh}>{fresh > 9 ? "9+" : fresh}</span>}
      </span>
      {title && <span className={styles.title}>{title}</span>}
      {subtitle && (
        <span className={cx(styles.subtitle, complete && styles.complete)}>{subtitle}</span>
      )}
    </>
  );
  return to ? (
    <Link to={to} className={styles.story} aria-label={label}>
      {body}
    </Link>
  ) : (
    <span className={styles.story} role="img" aria-label={label}>
      {body}
    </span>
  );
}
