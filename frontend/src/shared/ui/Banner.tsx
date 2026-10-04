import type { ReactNode } from "react";

import { cx } from "@/shared/lib/cx";
import { AnimatePresence, motion, useSpring } from "@/shared/motion";

import { Icon, type IconName } from "./Icon";
import styles from "./Banner.module.css";

const ICON: Record<"info" | "warning" | "danger", IconName> = {
  info: "clock",
  warning: "alert",
  danger: "alert",
};

/**
 * A message that stays true until it changes (offline, a wrong password, your turn to pick).
 * Inline at the top of the content it concerns; `floating` pins it to the top of the screen
 * (only for app-wide notices such as "a new version is ready"). Short confirmations use Toast.
 */
export function Banner({
  open = true,
  tone = "info",
  title,
  message,
  actions,
  floating = false,
}: {
  open?: boolean;
  tone?: "info" | "warning" | "danger";
  title: string;
  message?: string;
  actions?: ReactNode;
  floating?: boolean;
}) {
  const spring = useSpring("gentle");
  const from = floating ? { y: "-120%" } : { opacity: 0 };
  const to = floating ? { y: 0 } : { opacity: 1 };
  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className={cx(styles.banner, styles[tone], floating && styles.floating)}
          role={tone === "danger" ? "alert" : "status"}
          initial={from}
          animate={to}
          exit={from}
          transition={spring}
        >
          <span className={styles.icon} aria-hidden="true">
            <Icon name={ICON[tone]} size={20} />
          </span>
          <div className={styles.text}>
            <p className={styles.title}>{title}</p>
            {message && <p className={styles.message}>{message}</p>}
          </div>
          {actions && <div className={styles.actions}>{actions}</div>}
        </motion.div>
      )}
    </AnimatePresence>
  );
}
