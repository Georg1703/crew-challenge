import { cx } from "@/shared/lib/cx";
import { usePress } from "@/shared/lib/usePress";
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

const SHOWN_PEOPLE = 3;

/**
 * The reactions under a card, one chip per emoji in the order each was first used: the emoji, up
 * to three small avatars, then "+N". The viewer's chip is highlighted and pressed. A tap toggles
 * your reaction to that emoji; press and hold (or the context menu) asks who reacted.
 */
export function ReactionChips({
  chips,
  onToggle,
  onHold,
}: {
  chips: ReactionChip[];
  onToggle: (emoji: string) => void;
  onHold: (emoji: string) => void;
}) {
  return (
    <ul className={styles.chips}>
      <AnimatePresence initial={false}>
        {chips.map((chip) => (
          <Chip key={chip.emoji} chip={chip} onToggle={onToggle} onHold={onHold} />
        ))}
      </AnimatePresence>
    </ul>
  );
}

function Chip({
  chip,
  onToggle,
  onHold,
}: {
  chip: ReactionChip;
  onToggle: (emoji: string) => void;
  onHold: (emoji: string) => void;
}) {
  const spring = useSpring("bouncy");
  const press = usePress({
    onPress: () => onToggle(chip.emoji),
    onLongPress: () => onHold(chip.emoji),
  });
  const shown = chip.people.slice(0, SHOWN_PEOPLE);
  const extra = chip.people.length - shown.length;
  return (
    <motion.li
      className={styles.item}
      initial={{ opacity: 0, scale: 0.6 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.6 }}
      transition={spring}
    >
      <button
        type="button"
        className={cx(styles.chip, chip.mine && styles.mine)}
        aria-pressed={chip.mine}
        aria-label={chip.label}
        {...press}
      >
        <span className={styles.emoji} aria-hidden="true">
          {chip.emoji}
        </span>
        <span className={styles.people} aria-hidden="true">
          {shown.map((person) => (
            <Avatar key={person.id} name={person.name} seed={person.seed} size="xs" />
          ))}
          {extra > 0 && <span className={styles.more}>{`+${extra}`}</span>}
        </span>
      </button>
    </motion.li>
  );
}
