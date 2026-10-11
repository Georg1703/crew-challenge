import { NavLink } from "react-router";

import { cx } from "@/shared/lib/cx";
import { motion, pressScale, useSpring } from "@/shared/motion";

import { Icon, type IconName } from "./Icon";
import styles from "./TabBar.module.css";

export interface Tab {
  to: string;
  label: string;
  icon: IconName;
  end?: boolean;
  /** A number on the icon when above zero ("9+" past nine), and what it means for screen readers. */
  badge?: { count: number; label: string };
}

/** The raised button in the middle of the bar (check in), with an optional count. */
export interface TabAction {
  label: string;
  icon: IconName;
  onClick: () => void;
  /** Shown in a small bubble when above zero, for example check-ins left today. */
  count?: number;
  /** 0 to 1: a thin ring around the button while something runs (uploads). Say it in `label`. */
  progress?: number;
  /** Placed after this many tabs (default: the middle). */
  after?: number;
}

export function TabBar({
  tabs,
  label,
  action,
}: {
  tabs: Tab[];
  label: string;
  action?: TabAction;
}) {
  const spring = useSpring("snappy");
  const pop = useSpring("bouncy");
  const split = action?.after ?? Math.ceil(tabs.length / 2);
  const button = action && (
    <span className={styles.actionSlot} key="action">
      <motion.button
        type="button"
        className={styles.action}
        aria-label={action.count ? `${action.label} (${action.count})` : action.label}
        onClick={action.onClick}
        whileTap={{ scale: pressScale }}
        transition={spring}
      >
        <Icon name={action.icon} size={28} />
        {action.progress !== undefined && (
          <svg viewBox="0 0 64 64" className={styles.progress} aria-hidden="true">
            <circle cx="32" cy="32" r="30" className={styles.progressTrack} />
            <motion.circle
              cx="32"
              cy="32"
              r="30"
              transform="rotate(-90 32 32)"
              className={styles.progressFill}
              initial={false}
              animate={{ pathLength: Math.min(Math.max(action.progress, 0), 1) }}
              transition={spring}
            />
          </svg>
        )}
        {action.count ? (
          <motion.span
            key={action.count}
            className={styles.count}
            aria-hidden="true"
            initial={{ scale: 0.6, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={pop}
          >
            {action.count}
          </motion.span>
        ) : null}
      </motion.button>
    </span>
  );
  const links = tabs.map((tab) => (
    <NavLink
      key={tab.to}
      to={tab.to}
      end={tab.end}
      className={({ isActive }) => cx(styles.tab, isActive && styles.active)}
      aria-label={tab.badge?.count ? `${tab.label}, ${tab.badge.label}` : undefined}
    >
      {({ isActive }) => (
        <>
          {isActive && (
            <motion.span
              layoutId="tab-indicator"
              className={styles.indicator}
              transition={spring}
            />
          )}
          <span className={styles.icon}>
            <Icon name={tab.icon} />
            {tab.badge?.count ? (
              <span className={styles.badge} aria-hidden="true">
                {tab.badge.count > 9 ? "9+" : tab.badge.count}
              </span>
            ) : null}
          </span>
          <span className={styles.label}>{tab.label}</span>
        </>
      )}
    </NavLink>
  ));
  return (
    <nav className={styles.bar} aria-label={label}>
      {links.slice(0, split)}
      {button}
      {links.slice(split)}
    </nav>
  );
}
