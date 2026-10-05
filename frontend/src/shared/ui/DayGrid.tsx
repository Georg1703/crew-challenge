import { Fragment, type ReactNode } from "react";

import styles from "./DayGrid.module.css";
import { DayMark, type DayState } from "./DayMark";

/** Days per line: a month splits into two halves (1-16, 17-31) so the squares stay readable. */
const PER_LINE = 16;

/**
 * A month at a glance: one row per person, one square per day, in two halves with the day
 * numbers above each half.
 */
export function DayGrid({
  label,
  days,
  rows,
  dayName,
  todayIndex,
}: {
  label: string;
  /** Day of the month for each column (1..31). */
  days: number[];
  rows: { key: string; name: string; leading?: ReactNode; states: DayState[] }[];
  /** The accessible name of one square, for example "Ana, 12: done". */
  dayName: (row: string, day: number, state: DayState) => string;
  /** The column for today, if it is in this month. */
  todayIndex?: number;
}) {
  const halves = Array.from({ length: Math.ceil(days.length / PER_LINE) }, (_, h) => h * PER_LINE);
  return (
    <div className={styles.grid} role="table" aria-label={label}>
      {halves.map((from) => {
        const columns = days.slice(from, from + PER_LINE);
        return (
          <Fragment key={from}>
            <div className={styles.row} role="row">
              <span className={styles.name} role="columnheader" />
              <span className={styles.cells} aria-hidden="true">
                {columns.map((day, i) => (
                  <span
                    key={day}
                    className={from + i === todayIndex ? styles.todayNumber : styles.dayNumber}
                  >
                    {day}
                  </span>
                ))}
              </span>
            </div>
            {rows.map((row) => (
              <div key={row.key} className={styles.row} role="row">
                <span className={styles.name} role="rowheader">
                  {row.leading}
                  <span className={styles.nameText}>{row.name}</span>
                </span>
                <span className={styles.cells}>
                  {row.states.slice(from, from + PER_LINE).map((state, i) => (
                    <span key={i} role="cell" className={styles.cell}>
                      <DayMark
                        state={state}
                        size="sm"
                        current={from + i === todayIndex}
                        label={dayName(row.name, columns[i] ?? from + i + 1, state)}
                      />
                    </span>
                  ))}
                </span>
              </div>
            ))}
          </Fragment>
        );
      })}
    </div>
  );
}
