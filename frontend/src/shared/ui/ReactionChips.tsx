import { cx } from "@/shared/lib/cx";
import { usePress } from "@/shared/lib/usePress";
import { useRef } from "react";

import { AnimatePresence, motion, useSpring } from "@/shared/motion";

import { Avatar } from "./Avatar";
import styles from "./ReactionChips.module.css";

type Person = { id: string; name: string; seed: string };

export interface ReactionChip {
  emoji: string;
  /** Who used it, in the order they did. */
  people: Person[];
  /** The viewer's own reaction. */
  mine: boolean;
  /** Read by screen readers: "fire, from you and Ana". */
  label: string;
}

/**
 * A card's reactions, one small chip per emoji in the order each was first used: the emoji and
 * who used it (their avatar when it is one person, else how many). The viewer's chip is highlighted
 * and pressed. A tap toggles your reaction to that emoji (with the chip's place, for an
 * `EmojiFlight`); press and hold (or the context menu) asks who reacted. `landing` keeps one chip
 * invisible until its flying emoji arrives; chips leave and make room without a jump.
 */
export function ReactionChips({
  chips,
  onToggle,
  onHold,
  landing = null,
}: {
  chips: ReactionChip[];
  onToggle: (emoji: string, from: DOMRect) => void;
  onHold: (emoji: string) => void;
  /** The emoji whose chip waits, invisible, for its flight to land. */
  landing?: string | null;
}) {
  return (
    <ul className={styles.chips}>
      <AnimatePresence initial={false} mode="popLayout">
        {chips.map((chip) => (
          <Chip
            key={chip.emoji}
            chip={chip}
            landing={chip.emoji === landing}
            onToggle={onToggle}
            onHold={onHold}
          />
        ))}
      </AnimatePresence>
    </ul>
  );
}

function Chip({
  chip,
  landing,
  onToggle,
  onHold,
}: {
  chip: ReactionChip;
  landing: boolean;
  onToggle: (emoji: string, from: DOMRect) => void;
  onHold: (emoji: string) => void;
}) {
  const spring = useSpring("snappy");
  const button = useRef<HTMLButtonElement>(null);
  const press = usePress({
    onPress: () => {
      const from = button.current?.getBoundingClientRect();
      if (from) onToggle(chip.emoji, from);
    },
    onLongPress: () => onHold(chip.emoji),
  });
  const [only] = chip.people;
  return (
    <motion.li
      layout="position"
      className={styles.item}
      initial={landing ? { opacity: 0, scale: 1 } : { opacity: 0, scale: 0.6 }}
      animate={landing ? { opacity: 0, scale: 1 } : { opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.6 }}
      transition={spring}
    >
      <button
        ref={button}
        type="button"
        data-emoji={chip.emoji}
        className={cx(styles.chip, chip.mine && styles.mine)}
        aria-pressed={chip.mine}
        aria-label={chip.label}
        {...press}
      >
        <span className={styles.emoji} aria-hidden="true">
          {chip.emoji}
        </span>
        {chip.people.length === 1 && only ? (
          <span className={styles.people} aria-hidden="true">
            <Avatar name={only.name} seed={only.seed} size="xs" />
          </span>
        ) : (
          <span className={styles.count} aria-hidden="true">
            {chip.people.length}
          </span>
        )}
      </button>
    </motion.li>
  );
}
