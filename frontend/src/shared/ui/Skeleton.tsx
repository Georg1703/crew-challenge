import styles from "./Skeleton.module.css";

/** Placeholder block while data loads. Screens show skeletons, not spinners, for content. */
export function Skeleton({ lines = 3 }: { lines?: number }) {
  return (
    <div className={styles.group} aria-hidden="true">
      {Array.from({ length: lines }, (_, i) => (
        <span key={i} className={styles.line} />
      ))}
    </div>
  );
}
