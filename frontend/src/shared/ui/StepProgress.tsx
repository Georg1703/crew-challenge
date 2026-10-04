import { cx } from "@/shared/lib/cx";

import styles from "./StepProgress.module.css";

/** "Step 2 of 5" as segments, for multi-step forms. */
export function StepProgress({
  current,
  total,
  label,
}: {
  current: number;
  total: number;
  label: string;
}) {
  return (
    <div
      className={styles.bar}
      role="progressbar"
      aria-label={label}
      aria-valuemin={1}
      aria-valuemax={total}
      aria-valuenow={current}
    >
      {Array.from({ length: total }, (_, index) => (
        <span key={index} className={cx(styles.segment, index < current && styles.done)} />
      ))}
    </div>
  );
}
