import type { ComponentProps } from "react";

import { cx } from "@/shared/lib/cx";

import styles from "./Card.module.css";

/** A group of related content on a surface. `tone="accent"` highlights one card (your turn). */
export function Card({
  tone = "default",
  className,
  ...rest
}: ComponentProps<"section"> & { tone?: "default" | "accent" }) {
  return (
    <section className={cx(styles.card, tone === "accent" && styles.accent, className)} {...rest} />
  );
}
