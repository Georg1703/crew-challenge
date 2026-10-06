import { useEffect, useRef, useState, type KeyboardEvent, type MouseEvent } from "react";

import { cx } from "@/shared/lib/cx";
import { holdToConfirm, motion, useReducedMotion } from "@/shared/motion";

import styles from "./HoldButton.module.css";
import { Icon } from "./Icon";

/**
 * Press and hold to confirm (the check-in). A fill sweeps across while held; letting go early
 * cancels, so it never fires by accident and cannot fire twice. Keyboard and screen readers
 * press it like a normal button (Enter or Space confirms at once).
 */
export function HoldButton({
  label,
  doneLabel,
  done = false,
  disabled = false,
  onConfirm,
}: {
  label: string;
  doneLabel: string;
  done?: boolean;
  disabled?: boolean;
  onConfirm: () => void;
}) {
  const [holding, setHolding] = useState(false);
  const timer = useRef<number | undefined>(undefined);
  const reduced = useReducedMotion();
  const inactive = disabled || done;

  const stop = () => {
    window.clearTimeout(timer.current);
    setHolding(false);
  };
  useEffect(() => () => window.clearTimeout(timer.current), []);

  const start = () => {
    if (inactive) return;
    setHolding(true);
    timer.current = window.setTimeout(() => {
      setHolding(false);
      onConfirm();
    }, holdToConfirm.ms);
  };

  // A keyboard "click" has detail 0: confirm at once. Pointer clicks are handled by the hold.
  const onClick = (event: MouseEvent) => {
    if (event.detail === 0 && !inactive) onConfirm();
  };
  const onKeyDown = (event: KeyboardEvent) => {
    if (event.key === " ") event.preventDefault(); // avoid scrolling; Space still clicks
  };

  return (
    <button
      type="button"
      className={cx(styles.button, done && styles.done, holding && styles.holding)}
      disabled={disabled}
      aria-disabled={done || undefined}
      onPointerDown={(event) => event.button === 0 && start()}
      onPointerUp={stop}
      onPointerLeave={stop}
      onPointerCancel={stop}
      onContextMenu={(event) => event.preventDefault()}
      onClick={onClick}
      onKeyDown={onKeyDown}
    >
      {!done && (
        <motion.span
          className={styles.fill}
          aria-hidden="true"
          initial={false}
          animate={reduced ? { opacity: holding ? 0.35 : 0 } : { scaleX: holding ? 1 : 0 }}
          transition={holding ? holdToConfirm.fill : holdToConfirm.release}
        />
      )}
      <span className={styles.content}>
        {done && <Icon name="check" size={20} />}
        {done ? doneLabel : label}
      </span>
    </button>
  );
}
