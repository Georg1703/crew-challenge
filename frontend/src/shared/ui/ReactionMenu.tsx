import { useEffect, useRef, type RefObject } from "react";

import { cx } from "@/shared/lib/cx";
import { AnimatePresence, motion, useSpring } from "@/shared/motion";

import { Icon } from "./Icon";
import styles from "./ReactionMenu.module.css";

/**
 * The quick row of reactions: a small popover above the button that opened it, with a few emoji
 * buttons, "+" for any emoji and, when there are reactions, "who reacted". Picking closes it; so do
 * Escape and a tap outside. Focus moves into it and back to the opener.
 */
export function ReactionMenu({
  open,
  onClose,
  label,
  emojis,
  selected,
  onPick,
  moreLabel,
  onMore,
  whoLabel,
  onWho,
  anchor,
}: {
  open: boolean;
  onClose: () => void;
  /** The menu's name: "React". */
  label: string;
  emojis: string[];
  /** The viewer's reaction, shown pressed. */
  selected?: string | null;
  /** The emoji and where its button was (for an `EmojiFlight`). */
  onPick: (emoji: string, from: DOMRect) => void;
  /** "+": "More emojis". */
  moreLabel: string;
  onMore: () => void;
  /** Shown only with `onWho`: "Who reacted". */
  whoLabel?: string;
  onWho?: () => void;
  /** The button that opens it: a tap there toggles it instead of closing and reopening. */
  anchor?: RefObject<HTMLElement | null>;
}) {
  const panel = useRef<HTMLDivElement>(null);
  const spring = useSpring("snappy");

  useEffect(() => {
    if (!open) return;
    const previous = document.activeElement as HTMLElement | null;
    panel.current?.querySelector("button")?.focus({ preventScroll: true }); // no jump on phones
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      event.preventDefault();
      onClose();
    };
    const onDown = (event: PointerEvent) => {
      const target = event.target as Node;
      if (panel.current?.contains(target) || anchor?.current?.contains(target)) return;
      onClose();
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("pointerdown", onDown, true);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("pointerdown", onDown, true);
      previous?.focus({ preventScroll: true });
    };
  }, [open, onClose, anchor]);

  const choose = (action: () => void) => () => {
    onClose();
    action();
  };

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          ref={panel}
          className={styles.menu}
          role="menu"
          aria-label={label}
          initial={{ opacity: 0, scale: 0.8, y: 8 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.8, y: 8 }}
          transition={spring}
        >
          <div className={styles.row}>
            {emojis.map((emoji) => (
              <button
                key={emoji}
                type="button"
                role="menuitemradio"
                aria-checked={selected === emoji}
                className={cx(styles.emoji, selected === emoji && styles.selected)}
                onClick={(event) => {
                  const from = event.currentTarget.getBoundingClientRect();
                  choose(() => onPick(emoji, from))();
                }}
              >
                {emoji}
              </button>
            ))}
            <button
              type="button"
              role="menuitem"
              className={styles.more}
              aria-label={moreLabel}
              onClick={choose(onMore)}
            >
              <Icon name="plus" />
            </button>
          </div>
          {onWho && whoLabel && (
            <button type="button" role="menuitem" className={styles.who} onClick={choose(onWho)}>
              <Icon name="users" size={16} />
              {whoLabel}
            </button>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  );
}
