import type { ReactNode } from "react";
import { Link } from "react-router";

import { cx } from "@/shared/lib/cx";

import styles from "./ListRow.module.css";

/** Rows sit in one List: one surface, dividers between rows, never a card per row. */
export function List({ label, children }: { label?: string; children: ReactNode }) {
  return (
    <ul className={styles.list} aria-label={label}>
      {children}
    </ul>
  );
}

interface ListRowProps {
  /** An Avatar, an icon tile or a thumbnail. */
  leading?: ReactNode;
  title: ReactNode;
  subtitle?: ReactNode;
  /** One trailing item: a StatusPill, a small Button or nothing (links get a chevron). */
  trailing?: ReactNode;
  /** Makes the whole row a link. */
  to?: string;
}

/** A member, an invite, a setting: leading visual, title, one secondary line, one trailing item. */
export function ListRow({ leading, title, subtitle, trailing, to }: ListRowProps) {
  const body = (
    <>
      {leading && <span className={styles.leading}>{leading}</span>}
      <span className={styles.text}>
        <span className={styles.title}>{title}</span>
        {subtitle && <span className={styles.subtitle}>{subtitle}</span>}
      </span>
      {trailing && <span className={styles.trailing}>{trailing}</span>}
    </>
  );
  return (
    <li className={styles.item}>
      {to ? (
        <Link to={to} className={cx(styles.row, styles.link)}>
          {body}
        </Link>
      ) : (
        <div className={styles.row}>{body}</div>
      )}
    </li>
  );
}

/** A 40px rounded tile holding an icon, for rows without an avatar. */
export function IconTile({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "neutral" | "accent";
}) {
  return (
    <span className={cx(styles.tile, tone === "accent" && styles.tileAccent)}>{children}</span>
  );
}
