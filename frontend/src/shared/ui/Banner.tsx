import type { ReactNode } from "react";

import { AnimatePresence, motion, useSpring } from "@/shared/motion";

import styles from "./Banner.module.css";

/** A persistent message pinned to the top that needs a decision (unlike a Toast, it stays). */
export function Banner({
  open,
  message,
  actions,
}: {
  open: boolean;
  message: string;
  actions: ReactNode;
}) {
  const spring = useSpring("gentle");
  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className={styles.banner}
          role="status"
          initial={{ y: "-120%" }}
          animate={{ y: 0 }}
          exit={{ y: "-120%" }}
          transition={spring}
        >
          <p className={styles.message}>{message}</p>
          <div className={styles.actions}>{actions}</div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
