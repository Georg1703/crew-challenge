import { useLayoutEffect } from "react";
import { createPortal } from "react-dom";

import { emojiFlight, useAnimate } from "@/shared/motion";

import styles from "./EmojiFlight.module.css";

export interface Flight {
  /** New for every flight, so a second pick restarts it. */
  id: number;
  emoji: string;
  /** Where it was picked (the button under the finger). */
  from: DOMRect;
  /** What it grows over (the card's photo, number or milestone). */
  via: DOMRect;
  /** Where it lands, read once it gets there (the chip may still be sliding into place). */
  to: () => DOMRect | null;
}

const center = (rect: DOMRect) => ({
  x: rect.left + rect.width / 2,
  y: rect.top + rect.height / 2,
});

/**
 * A picked emoji flying into place above everything: from the finger it grows big over the
 * card, wiggles left and right, then shrinks into its chip. Calls `onDone` when it lands (or at once when
 * there is nowhere to land). Purely decorative: hidden from screen readers.
 */
export function EmojiFlight({ flight, onDone }: { flight: Flight; onDone: () => void }) {
  const [scope, animate] = useAnimate<HTMLSpanElement>();

  useLayoutEffect(() => {
    let stopped = false;
    const from = center(flight.from);
    const via = center(flight.via);
    async function fly() {
      await animate(
        scope.current,
        {
          x: [from.x, via.x],
          y: [from.y, via.y],
          scale: [emojiFlight.start, emojiFlight.peak],
          rotate: [0, emojiFlight.wiggle[0] ?? 0],
          opacity: 1,
        },
        emojiFlight.out,
      );
      await animate(scope.current, { rotate: emojiFlight.wiggle }, emojiFlight.hold);
      const target = flight.to();
      if (stopped) return;
      if (target) {
        const to = center(target);
        await animate(
          scope.current,
          { x: to.x, y: to.y, scale: emojiFlight.land },
          emojiFlight.back,
        );
      }
      if (!stopped) onDone();
    }
    void fly();
    return () => {
      stopped = true;
    };
    // One flight per id; onDone and the rects belong to it.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [flight.id]);

  return createPortal(
    <span ref={scope} className={styles.flyer} aria-hidden="true">
      {flight.emoji}
    </span>,
    document.body,
  );
}
