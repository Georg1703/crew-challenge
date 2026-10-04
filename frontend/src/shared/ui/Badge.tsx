import type { ReactNode } from "react";

import { cx } from "@/shared/lib/cx";

import styles from "./Badge.module.css";

export function Badge({
  tone = "neutral",
  children,
}: {
  tone?: "neutral" | "accent" | "success" | "danger";
  children: ReactNode;
}) {
  return <span className={cx(styles.badge, styles[tone])}>{children}</span>;
}
