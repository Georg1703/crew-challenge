import { NavLink } from "react-router";

import { cx } from "@/shared/lib/cx";
import { motion, useSpring } from "@/shared/motion";

import { Icon, type IconName } from "./Icon";
import styles from "./TabBar.module.css";

export interface Tab {
  to: string;
  label: string;
  icon: IconName;
  end?: boolean;
}

export function TabBar({ tabs, label }: { tabs: Tab[]; label: string }) {
  const spring = useSpring("snappy");
  return (
    <nav className={styles.bar} aria-label={label}>
      {tabs.map((tab) => (
        <NavLink
          key={tab.to}
          to={tab.to}
          end={tab.end}
          className={({ isActive }) => cx(styles.tab, isActive && styles.active)}
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
              <Icon name={tab.icon} />
              <span className={styles.label}>{tab.label}</span>
            </>
          )}
        </NavLink>
      ))}
    </nav>
  );
}
