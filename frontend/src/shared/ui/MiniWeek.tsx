import { cx } from "@/shared/lib/cx";

import type { DayState } from "./DayMark";
import styles from "./MiniWeek.module.css";

/**
 * The last seven days as small bars (the same shapes as `DayBars`: tall green done, short red
 * missed, outlined to do), today marked with the focus ring. Read as one summary in `label`.
 */
export function MiniWeek({
  days,
  label,
}: {
  days: { key: string; state: DayState; today?: boolean }[];
  label: string;
}) {
  return (
    <span className={styles.week} role="img" aria-label={label}>
      {days.map((day) => (
        <span
          key={day.key}
          className={cx(
            styles.bar,
            styles[day.state === "not_due" ? "notDue" : day.state],
            day.today && styles.today,
          )}
        />
      ))}
    </span>
  );
}
