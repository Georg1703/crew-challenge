import { useState, type ReactNode } from "react";

import { cx } from "@/shared/lib/cx";
import { dialTurn, motion, useReducedMotion } from "@/shared/motion";

import styles from "./Dial.module.css";

const SIZE = 120;
const RADIUS = 52;
const NUMBERS_RADIUS = 36;
const GAP_DEGREES = 8;
const TURNS = 4; // full turns before it stops on the drawn arc

function point(degrees: number, radius = RADIUS): [number, number] {
  const radians = ((degrees - 90) * Math.PI) / 180;
  return [SIZE / 2 + radius * Math.cos(radians), SIZE / 2 + radius * Math.sin(radians)];
}

function arc(start: number, end: number): string {
  const [x1, y1] = point(start);
  const [x2, y2] = point(end);
  return `M ${x1} ${y1} A ${RADIUS} ${RADIUS} 0 0 1 ${x2} ${y2}`;
}

/**
 * The Wheel of Doom's dial, in the day ring's shape: one arc per punishment (2 to 8, numbered
 * from the top, clockwise) and a marker on the ring. When `drawn` is set the marker turns to that
 * arc (a few full turns, slowing down; at once with reduced motion or when it is already drawn on
 * the first render) and the arc lights up once it stops. `size="sm"` is a mark: no numbers.
 */
export function Dial({
  count,
  drawn = null,
  label,
  size = "lg",
  children,
  onStopped,
}: {
  count: number;
  /** The drawn punishment's position (1 to `count`), or null before the spin. */
  drawn?: number | null;
  /** What the dial says, for screen readers ("A dial with 5 punishments; 3 was drawn"). */
  label: string;
  size?: "lg" | "sm";
  /** Shown in the middle: "?", the drawn number. */
  children?: ReactNode;
  /** The marker stopped on the drawn arc. */
  onStopped?: () => void;
}) {
  const reduced = useReducedMotion();
  const [lit, setLit] = useState(drawn); // drawn before the first render: lit at once
  const step = 360 / count;
  const target = drawn === null ? 0 : TURNS * 360 + (drawn - 1) * step + step / 2;

  return (
    <div className={cx(styles.dial, styles[size])} role="img" aria-label={label}>
      <svg viewBox={`0 0 ${SIZE} ${SIZE}`} className={styles.svg} aria-hidden="true">
        {Array.from({ length: count }, (_, index) => (
          <path
            key={index}
            d={arc(index * step + GAP_DEGREES / 2, (index + 1) * step - GAP_DEGREES / 2)}
            className={cx(styles.arc, lit === index + 1 && styles.drawn)}
          />
        ))}
      </svg>
      {size === "lg" &&
        Array.from({ length: count }, (_, index) => {
          const [x, y] = point(index * step + step / 2, NUMBERS_RADIUS);
          return (
            <span
              key={index}
              aria-hidden="true"
              className={cx(styles.number, lit === index + 1 && styles.drawnNumber)}
              style={{ left: `${(x / SIZE) * 100}%`, top: `${(y / SIZE) * 100}%` }}
            >
              {index + 1}
            </span>
          );
        })}
      <motion.div
        className={styles.turn}
        initial={false}
        animate={{ rotate: target }}
        transition={reduced ? { duration: 0 } : dialTurn}
        onAnimationComplete={() => {
          if (drawn === null) return;
          setLit(drawn);
          onStopped?.();
        }}
        aria-hidden="true"
      >
        <span className={styles.marker} />
      </motion.div>
      {children !== undefined && <div className={styles.center}>{children}</div>}
    </div>
  );
}
