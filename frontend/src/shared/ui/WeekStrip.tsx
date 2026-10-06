import styles from "./WeekStrip.module.css";
import { DayMark, type DayState } from "./DayMark";

/**
 * Seven days, Monday to Sunday, as shapes with the weekday's letter under each, and a dot under
 * the days with proof (say so in `name` too).
 */
export function WeekStrip({
  label,
  days,
}: {
  label: string;
  days: {
    key: string;
    letter: string;
    name: string;
    state: DayState;
    today?: boolean;
    proof?: boolean;
  }[];
}) {
  return (
    <ol className={styles.strip} aria-label={label}>
      {days.map((day) => (
        <li key={day.key} className={styles.day}>
          <DayMark state={day.state} label={day.name} current={day.today} />
          <span className={styles.letter} aria-hidden="true">
            {day.letter}
          </span>
          {day.proof && <span className={styles.dot} aria-hidden="true" />}
        </li>
      ))}
    </ol>
  );
}
