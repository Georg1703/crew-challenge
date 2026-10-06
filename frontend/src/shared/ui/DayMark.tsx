import { cx } from "@/shared/lib/cx";

import styles from "./DayMark.module.css";
import { Icon } from "./Icon";

/** How one day looks for one person and challenge (matches the API's day states). */
export type DayState =
  "done" | "partial" | "todo" | "open" | "missed" | "not_due" | "future" | "outside";

/**
 * A day as a small shape, readable without color: a filled check (done), a half ring (partial),
 * a ring (due or open), a cross (missed), a dot (not due), a faint ring (future), nothing
 * (outside). `size="sm"` for the month grid.
 */
export function DayMark({
  state,
  label,
  size = "md",
  current = false,
}: {
  state: DayState;
  label: string;
  size?: "sm" | "md";
  current?: boolean;
}) {
  return (
    <span
      role="img"
      aria-label={label}
      className={cx(
        styles.mark,
        styles[size],
        styles[state === "not_due" ? "notDue" : state],
        current && styles.current,
      )}
    >
      {state === "done" && size === "md" && <Icon name="check" size={14} />}
      {state === "missed" && size === "md" && <Icon name="close" size={12} />}
    </span>
  );
}
