import type { ReactNode } from "react";

import { cx } from "@/shared/lib/cx";

import styles from "./Screen.module.css";

/** Page layout: centered column, safe areas, room for the tab bar. Every route uses it. */
export function Screen({
  title,
  action,
  withTabBar = true,
  children,
}: {
  title?: string;
  action?: ReactNode;
  withTabBar?: boolean;
  children: ReactNode;
}) {
  return (
    <main className={cx(styles.screen, withTabBar && styles.withTabBar)}>
      <div className={styles.column}>
        {(title || action) && (
          <header className={styles.header}>
            {title && <h1 className={styles.title}>{title}</h1>}
            {action}
          </header>
        )}
        {children}
      </div>
    </main>
  );
}

export function Stack({ gap = "md", children }: { gap?: "sm" | "md" | "lg"; children: ReactNode }) {
  const className = { sm: styles.stackSm, md: styles.stackMd, lg: styles.stackLg }[gap];
  return <div className={className}>{children}</div>;
}
