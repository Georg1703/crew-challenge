import { cx } from "@/shared/lib/cx";

import styles from "./DayBars.module.css";
import type { DayState } from "./DayMark";

/**
 * A day as a thin bar: tall and green when done, short and red when missed, outlined when due.
 * `proof` adds the dot under it (for a legend).
 */
export function DayBar({
  state,
  label,
  proof = false,
}: {
  state: DayState;
  label?: string;
  proof?: boolean;
}) {
  return (
    <span className={styles.single} role={label ? "img" : undefined} aria-label={label}>
      <span className={styles.slot}>
        <span className={cx(styles.bar, styles[cssName(state)])} />
      </span>
      {proof && <span className={styles.dot} />}
    </span>
  );
}

/**
 * A person's month as one row of bars, one per day. Screen readers get `label` (a summary such
 * as "Ana: 5 days done, 1 missed, 4 with proof") instead of 31 bars. `proofs` (one per day) adds
 * a row of dots under the days with proof; pass it to every row of a board so rows line up.
 */
export function DayBars({
  states,
  label,
  proofs,
}: {
  states: DayState[];
  label: string;
  proofs?: boolean[];
}) {
  return (
    <span className={styles.days} role="img" aria-label={label}>
      <span className={styles.bars}>
        {states.map((state, i) => (
          <span key={i} className={cx(styles.bar, styles[cssName(state)])} />
        ))}
      </span>
      {proofs && (
        <span className={styles.dots}>
          {states.map((_, i) => (
            <span key={i} className={styles.dotSlot}>
              {proofs[i] && <span className={styles.dot} />}
            </span>
          ))}
        </span>
      )}
    </span>
  );
}

/** The day numbers above a set of `DayBars`: the first, every fifth, the last and today. */
export function DayBarsAxis({ days, todayIndex }: { days: number[]; todayIndex?: number }) {
  const last = days.length - 1;
  return (
    <span className={styles.axis} aria-hidden="true">
      {days.map((day, i) => {
        const today = i === todayIndex;
        const shown = today || i === 0 || i === last || (day % 5 === 0 && last - i > 1);
        return (
          <span key={day} className={cx(styles.number, today && styles.today)}>
            {shown ? day : null}
          </span>
        );
      })}
    </span>
  );
}

function cssName(state: DayState): string {
  return state === "not_due" ? "notDue" : state;
}
