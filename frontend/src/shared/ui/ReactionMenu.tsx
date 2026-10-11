import { useEffect, useLayoutEffect, useRef, type RefObject } from "react";
import { createPortal } from "react-dom";

import { cx } from "@/shared/lib/cx";
import { AnimatePresence, motion, useSpring } from "@/shared/motion";

import { Icon, type IconName } from "./Icon";
import styles from "./ReactionMenu.module.css";

/** A row under the emojis: "Reply", "Delete", "Who reacted". */
export type MenuAction = {
  label: string;
  icon: IconName;
  onSelect: () => void;
  /** Deletes something: shown in the danger color. */
  danger?: boolean;
};

const EDGE = 8; // px kept clear of the screen's edges and of the opener

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
    window.addEventListener("scroll", onClose, { capture: true, passive: true });
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("pointerdown", onDown, true);
      window.removeEventListener("scroll", onClose, { capture: true });
      previous?.focus({ preventScroll: true });
    };
  }, [open, onClose, anchor]);

  // Place it before it is painted: over the opener's right edge, inside the screen.
  useLayoutEffect(() => {
    const menu = panel.current;
    const at = anchor?.current?.getBoundingClientRect();
    if (!open || !menu || !at) return;
    const width = menu.offsetWidth;
    const height = menu.offsetHeight;
    const above = at.top - height - EDGE;
    menu.style.left = `${Math.max(EDGE, Math.min(at.right - width, window.innerWidth - width - EDGE))}px`;
    menu.style.top = `${above >= EDGE ? above : at.bottom + EDGE}px`;
  }, [open, anchor]);

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
