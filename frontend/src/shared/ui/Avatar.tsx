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
  ring,
  label,
}: {
  name: string;
  seed: string;
  size?: "xs" | "sm" | "md" | "lg";
  /** Today's ring: checked in (`done`) or not yet (`todo`). Say it in `label` too. */
  ring?: "done" | "todo";
  /** Accessible name; defaults to `name`. */
  label?: string;
}) {
  return (
    <span
      className={cx(styles.avatar, styles[size], ring && styles[ring])}
      data-color={avatarColor(seed)}
      role="img"
      aria-label={label ?? name}
    >
      {initials(name)}
    </span>
  );
}

const STACK_MAX = 5;

/** Overlapping small avatars, up to five, then "+N". */
export function AvatarStack({
  members,
  label,
}: {
  members: { id: string; name: string; seed: string }[];
  label: string;
}) {
  const shown = members.slice(0, STACK_MAX);
  const extra = members.length - shown.length;
  return (
    <span className={styles.stack} role="img" aria-label={label}>
      {shown.map((member) => (
        <span
          key={member.id}
          aria-hidden="true"
          className={cx(styles.avatar, styles.sm)}
          data-color={avatarColor(member.seed)}
        >
          {initials(member.name)}
        </span>
      ))}
      {extra > 0 && (
        <span aria-hidden="true" className={cx(styles.avatar, styles.sm, styles.more)}>
          {`+${extra}`}
        </span>
      )}
    </span>
  );
}
