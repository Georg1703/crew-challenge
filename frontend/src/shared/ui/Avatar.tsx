import { cx } from "@/shared/lib/cx";

import styles from "./Avatar.module.css";

const COLORS = 5; // matches --color-avatar-1..5 in tokens.css

/** A stable color index (1..5) from the member's avatar seed. */
export function avatarColor(seed: string): number {
  let hash = 0;
  for (const char of seed) hash = (hash * 31 + char.charCodeAt(0)) >>> 0;
  return (hash % COLORS) + 1;
}

export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  const letters = parts.length > 1 ? [parts[0], parts[parts.length - 1]] : [parts[0] ?? "?"];
  return letters
    .map((part) => (part ?? "").charAt(0))
    .join("")
    .toUpperCase();
}

export function Avatar({
  name,
  seed,
  size = "md",
}: {
  name: string;
  seed: string;
  size?: "sm" | "md" | "lg";
}) {
  return (
    <span
      className={cx(styles.avatar, styles[size])}
      data-color={avatarColor(seed)}
      role="img"
      aria-label={name}
    >
      {initials(name)}
    </span>
  );
}
