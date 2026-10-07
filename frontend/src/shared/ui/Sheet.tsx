import {
  createContext,
  useContext,
  useEffect,
  useId,
  useRef,
  useState,
  type ReactNode,
} from "react";

import { AnimatePresence, motion, useSpring } from "@/shared/motion";

import { Icon } from "./Icon";
import styles from "./Sheet.module.css";

const Settled = createContext(true);

/**
 * False while the sheet slides in (true outside a sheet). Heavy content waits for it: the slide is
 * drawn frame by frame on the main thread, so building a big view during it stutters.
 */
export function useSheetSettled(): boolean {
  return useContext(Settled);
}

const slide = { open: { y: 0 }, closed: { y: "100%" } };

/** A bottom sheet dialog: slides up, closes on backdrop tap, Escape, or the close button. */
export function Sheet({
  open,
  onClose,
  title,
  closeLabel,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  closeLabel: string;
  children: ReactNode;
}) {
  const titleId = useId();
  const panel = useRef<HTMLDivElement>(null);
  const spring = useSpring("gentle");
  const [settled, setSettled] = useState(false);

  useEffect(() => {
    if (!open) return;
    const previous = document.activeElement as HTMLElement | null;
    panel.current?.focus();
    const onKey = (event: KeyboardEvent) => {
      // A layer above (the proof viewer) handles its own Escape first and marks it handled.
      if (event.key === "Escape" && !event.defaultPrevented) onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      previous?.focus();
    };
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open && (
        <div className={styles.root}>
          <motion.div
            className={styles.backdrop}
            onClick={onClose}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          />
          <motion.div
            ref={panel}
            className={styles.panel}
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
            tabIndex={-1}
            variants={slide}
            initial="closed"
            animate="open"
            exit="closed"
            transition={spring}
            onAnimationComplete={(name) => setSettled(name === "open")}
          >
            <div className={styles.handle} aria-hidden="true" />
            <header className={styles.header}>
              <h2 id={titleId} className={styles.title}>
                {title}
              </h2>
              <button
                type="button"
                className={styles.close}
                onClick={onClose}
                aria-label={closeLabel}
              >
                <Icon name="close" />
              </button>
            </header>
            <Settled.Provider value={settled}>{children}</Settled.Provider>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
