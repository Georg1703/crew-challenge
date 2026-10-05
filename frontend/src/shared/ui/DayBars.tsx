import { cx } from "@/shared/lib/cx";

import styles from "./DayBars.module.css";
import type { DayState } from "./DayMark";

/** A day as a thin bar: tall and green when done, short and red when missed, outlined when due. */
export function DayBar({ state, label }: { state: DayState; label?: string }) {
  return (
    <span className={styles.slot} role={label ? "img" : undefined} aria-label={label}>
      <span className={cx(styles.bar, styles[cssName(state)])} />
    </span>
  );
}

/**
 * A person's month as one row of bars, one per day. Screen readers get `label` (a summary such
 * as "Ana: 5 days done, 1 missed") instead of 31 bars.
 */
export function DayBars({ states, label }: { states: DayState[]; label: string }) {
  return (
    <span className={styles.bars} role="img" aria-label={label}>
      {states.map((state, i) => (
        <span key={i} className={cx(styles.bar, styles[cssName(state)])} />
      ))}
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
