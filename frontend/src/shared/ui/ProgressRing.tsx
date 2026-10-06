import type { ReactNode } from "react";

import { cx } from "@/shared/lib/cx";
import { AnimatePresence, motion, useSpring, variants } from "@/shared/motion";

import styles from "./ProgressRing.module.css";

export type RingSegment = "full" | "partial" | "empty";

const SIZE = 120;
const RADIUS = 52;
const GAP_DEGREES = 10;

function point(degrees: number): [number, number] {
  const radians = ((degrees - 90) * Math.PI) / 180;
  return [SIZE / 2 + RADIUS * Math.cos(radians), SIZE / 2 + RADIUS * Math.sin(radians)];
}

function arc(start: number, end: number): string {
  const [x1, y1] = point(start);
  const [x2, y2] = point(end);
  const large = end - start > 180 ? 1 : 0;
  return `M ${x1} ${y1} A ${RADIUS} ${RADIUS} 0 ${large} 1 ${x2} ${y2}`;
}

/**
 * The day ring: one segment per thing to do today. A segment fills with a spring when it is
 * done (half for partial); when all are full the ring is closed and `done` pops into the
 * center in place of `children`.
 */
export function ProgressRing({
  segments,
  label,
  children,
  done,
}: {
  segments: RingSegment[];
  /** What the ring says, for screen readers ("2 of 3 done today"). */
  label: string;
  children: ReactNode;
  /** Shown in the center once every segment is full. */
  done: ReactNode;
}) {
  const fill = useSpring("bouncy");
  const pop = useSpring("bouncy");
  const count = Math.max(segments.length, 1);
  const gap = segments.length > 1 ? GAP_DEGREES : 0;
  const step = 360 / count;
  const closed = segments.length > 0 && segments.every((s) => s === "full");

  return (
    <div className={cx(styles.ring, closed && styles.closed)} role="img" aria-label={label}>
      <svg viewBox={`0 0 ${SIZE} ${SIZE}`} className={styles.svg} aria-hidden="true">
        {(segments.length ? segments : (["empty"] as RingSegment[])).map((segment, index) => {
          const start = index * step + gap / 2;
          const end = start + step - gap;
          const path = count === 1 ? arc(0, 359.99) : arc(start, end);
          return (
            <g key={index}>
              <path d={path} className={styles.track} />
              <motion.path
                d={path}
                className={cx(styles.fill, segment === "partial" && styles.partial)}
                initial={false}
                animate={{
                  pathLength: segment === "full" ? 1 : segment === "partial" ? 0.5 : 0,
                  opacity: segment === "empty" ? 0 : 1, // a zero-length round cap is still a dot
                }}
                transition={fill}
              />
            </g>
          );
        })}
      </svg>
      <div className={styles.center}>
        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            key={closed ? "done" : "progress"}
            className={styles.centerContent}
            variants={variants.popIn}
            initial="hidden"
            animate="visible"
            exit="hidden"
            transition={pop}
          >
            {closed ? done : children}
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
}
