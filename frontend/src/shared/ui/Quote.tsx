import { cx } from "@/shared/lib/cx";

import { avatarColor } from "./Avatar";
import styles from "./Quote.module.css";

/**
 * What a message answers, as Telegram shows it: a bar and the name in the writer's avatar color,
 * then the first line of their text. With `onClick` it is a button (go to that message).
 */
export function Quote({
  name,
  seed,
  text,
  onClick,
  label,
}: {
  name: string;
  /** The writer's avatar seed: the bar and the name take its color. */
  seed: string;
  text: string;
  onClick?: () => void;
  /** The button's name for screen readers: "Go to Ana's comment". */
  label?: string;
}) {
  const body = (
    <>
      <span className={styles.name}>{name}</span>
      <span className={styles.text}>{text}</span>
    </>
  );
  const color = avatarColor(seed);
  return onClick ? (
    <button
      type="button"
      className={cx(styles.quote, styles.link)}
      data-color={color}
      aria-label={label}
      onClick={onClick}
    >
      {body}
    </button>
  ) : (
    <div className={styles.quote} data-color={color}>
      {body}
    </div>
  );
}
