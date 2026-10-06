import styles from "./DayDivider.module.css";

/** A day in a journal: its name, a line, and what happened ("5 check-ins, 9 proofs"). */
export function DayDivider({ title, summary }: { title: string; summary?: string }) {
  return (
    <div className={styles.divider}>
      <h2 className={styles.title}>{title}</h2>
      <span className={styles.line} aria-hidden="true" />
      {summary && <span className={styles.summary}>{summary}</span>}
    </div>
  );
}
