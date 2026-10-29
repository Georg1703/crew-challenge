import { Avatar } from "./Avatar";
import { Icon } from "./Icon";
import { List, ListRow } from "./ListRow";
import styles from "./MentionMenu.module.css";

export type MentionOption = {
  id: string;
  /** What the row says: "Everyone", or the member's name. */
  name: string;
  /** What goes after the `@` when it is not the name ("all"). */
  insert?: string;
  /** The member's avatar; none for "Everyone". */
  seed?: string;
};

/** The short list over the message box while an `@` is typed: a tap picks a row. */
export function MentionMenu({
  options,
  label,
  onPick,
}: {
  options: MentionOption[];
  label: string;
  onPick: (option: MentionOption) => void;
}) {
  if (options.length === 0) return null;
  return (
    <div className={styles.menu} role="group" aria-label={label}>
      <List>
        {options.map((option) => (
          <ListRow
            key={option.id}
            leading={
              option.seed ? (
                <Avatar name={option.name} seed={option.seed} size="sm" />
              ) : (
                <span className={styles.everyone}>
                  <Icon name="users" size={20} />
                </span>
              )
            }
            title={option.name}
            onClick={() => onPick(option)}
          />
        ))}
      </List>
    </div>
  );
}
