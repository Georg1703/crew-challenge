import type { ComponentProps } from "react";

import { cx } from "@/shared/lib/cx";

import styles from "./Card.module.css";

export function Card({ className, ...rest }: ComponentProps<"section">) {
  return <section className={cx(styles.card, className)} {...rest} />;
}
