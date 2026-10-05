import { cx } from "@/shared/lib/cx";
import { motion, useSpring } from "@/shared/motion";

import styles from "./ProgressBar.module.css";

/** How far toward a goal: a bar that springs to its new length. Full turns success green. */
export function ProgressBar({
  value,
  max,
  label,
}: {
  value: number;
  max: number;
  /** Read by screen readers, for example "12 of 20 pages". */
  label: string;
}) {
  const transition = useSpring("bouncy");
  const ratio = max > 0 ? Math.min(1, Math.max(0, value / max)) : 0;
  return (
    <div
      className={styles.track}
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={max}
      aria-valuenow={Math.min(value, max)}
    >
      <motion.div
        className={cx(styles.fill, ratio >= 1 && styles.full)}
        initial={false}
        animate={{ scaleX: ratio }}
        transition={transition}
      />
    </div>
  );
}
