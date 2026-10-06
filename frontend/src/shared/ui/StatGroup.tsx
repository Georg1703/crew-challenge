import { cx } from "@/shared/lib/cx";

import styles from "./StatGroup.module.css";

/** Up to three numbers side by side in one card, each with a short label under it. */
export function StatGroup({
  stats,
}: {
  stats: { key: string; value: string; label: string; tone?: "default" | "success" }[];
}) {
  return (
    <dl className={styles.group}>
      {stats.map((stat) => (
        <div key={stat.key} className={styles.stat}>
          <dt className={styles.label}>{stat.label}</dt>
          <dd className={cx(styles.value, stat.tone === "success" && styles.success)}>
            {stat.value}
          </dd>
        </div>
      ))}
    </dl>
  );
}
