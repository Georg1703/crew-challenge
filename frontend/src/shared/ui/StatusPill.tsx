import type { ReactNode } from "react";

import { cx } from "@/shared/lib/cx";

import { Icon } from "./Icon";
import styles from "./StatusPill.module.css";

export type StatusTone = "neutral" | "accent" | "success" | "warning" | "danger";

/**
 * A short label for where something stands (done, to do, missed, uploading, admin).
 * Meaning never rests on color alone: `success` shows a check.
 */
export function StatusPill({
  tone = "neutral",
  children,
}: {
  tone?: StatusTone;
  children: ReactNode;
}) {
  return (
    <span className={cx(styles.pill, styles[tone])}>
      {tone === "success" && <Icon name="check" size={14} />}
      {children}
    </span>
  );
}
