import styles from "./ChallengeChip.module.css";
import { Icon, type IconName } from "./Icon";

/** A challenge named in a sentence: its icon in a small accent circle, and its title. */
export function ChallengeChip({ icon, label }: { icon: IconName; label: string }) {
  return (
    <span className={styles.chip}>
      <span className={styles.icon} aria-hidden="true">
        <Icon name={icon} size={12} />
      </span>
      <span className={styles.label}>{label}</span>
    </span>
  );
}
