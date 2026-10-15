import { useEffect, type RefObject } from "react";
import { createPortal } from "react-dom";

import { cx } from "@/shared/lib/cx";
import { AnimatePresence, motion, useSpring } from "@/shared/motion";

import { Icon, type IconName } from "./Icon";
import styles from "./ReactionMenu.module.css";
import { usePopover } from "./usePopover";

/** A row under the emojis: "Reply", "Delete", "Who reacted". */
export type MenuAction = {
  label: string;
  icon: IconName;
  onSelect: () => void;
  /** Deletes something: shown in the danger color. */
  danger?: boolean;
};

/**
 * The quick row of reactions: a small popover above the button that opened it (below it when
 * there is no room), kept inside the screen, with a few emoji buttons, "+" for any emoji and,
 * under them, `actions` ("Reply", "Who reacted"). Picking closes it; so do Escape, a tap outside
 * and scrolling. Focus moves into it and back to the opener.
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
  actions = [],
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
  actions?: MenuAction[];
  /** The button that opens it: a tap there toggles it instead of closing and reopening. */
  anchor?: RefObject<HTMLElement | null>;
}) {
  const spring = useSpring("snappy");

  const panel = usePopover<HTMLDivElement>({ open, onClose, anchor }); // over its right edge

  useEffect(() => {
    if (!open) return;
    const previous = document.activeElement as HTMLElement | null;
    panel.current?.querySelector("button")?.focus({ preventScroll: true }); // no jump on phones
    return () => previous?.focus({ preventScroll: true });
  }, [open, panel]);

  const choose = (action: () => void) => () => {
    onClose();
    action();
  };

  return createPortal(
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
          {actions.map((action) => (
            <button
              key={action.label}
              type="button"
              role="menuitem"
              className={cx(styles.action, action.danger && styles.danger)}
              onClick={choose(action.onSelect)}
            >
              <Icon name={action.icon} size={16} />
              {action.label}
            </button>
          ))}
        </motion.div>
      )}
    </AnimatePresence>,
    document.body,
  );
}
