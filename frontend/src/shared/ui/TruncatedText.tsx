import { useCallback, useRef, useState } from "react";
import { createPortal } from "react-dom";

import { cx } from "@/shared/lib/cx";
import { AnimatePresence, motion, useSpring } from "@/shared/motion";

import styles from "./TruncatedText.module.css";
import { usePopover } from "./usePopover";

/**
 * A text on one line, cut with "..." where the line ends (a punishment), so rows of long and
 * short ones line up. A tap on a cut one shows the whole text in a small bubble over it (under
 * it when there is no room), inside the screen; a second tap, a tap outside, Escape or scrolling
 * closes it. A text that fits does nothing. The whole text stays in the page (screen readers read
 * it all; a mouse sees it on hover).
 */
export function TruncatedText({ text, className }: { text: string; className?: string }) {
  const line = useRef<HTMLSpanElement>(null);
  const [open, setOpen] = useState(false);
  const close = useCallback(() => setOpen(false), []);
  const spring = useSpring("snappy");
  const bubble = usePopover<HTMLDivElement>({ open, onClose: close, anchor: line, align: "start" });

  const toggle = () => {
    const cut = line.current !== null && line.current.scrollWidth > line.current.clientWidth;
    if (cut || open) setOpen(!open);
  };

  return (
    <>
      <span ref={line} className={cx(styles.line, className)} title={text} onClick={toggle}>
        {text}
      </span>
      {createPortal(
        <AnimatePresence>
          {open && (
            <motion.div
              ref={bubble}
              className={styles.bubble}
              aria-hidden="true"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              transition={spring}
            >
              {text}
            </motion.div>
          )}
        </AnimatePresence>,
        document.body,
      )}
    </>
  );
}
