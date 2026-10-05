import type { ReactNode } from "react";

import styles from "./DayGrid.module.css";
import { DayMark, type DayState } from "./DayMark";

/**
 * A month at a glance: one row per person, one small square per day. Day numbers are shown
 * every week so the grid stays readable on a phone.
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
  return (
    <div className={styles.grid} role="table" aria-label={label}>
      <div className={styles.row} role="row">
        <span className={styles.name} role="columnheader" />
        <span className={styles.cells} aria-hidden="true">
          {days.map((day, index) => (
            <span key={day} className={styles.dayNumber}>
              {index % 7 === 0 || index === todayIndex ? day : ""}
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
            {row.states.map((state, index) => (
              <span key={index} role="cell" className={styles.cell}>
                <DayMark
                  state={state}
                  size="sm"
                  current={index === todayIndex}
                  label={dayName(row.name, days[index] ?? index + 1, state)}
                />
              </span>
            ))}
          </span>
        </div>
      ))}
    </div>
  );
}
