import { useTranslation } from "react-i18next";

import type { Member } from "@/api";
import { Avatar, List, ListRow, Sheet } from "@/shared/ui";

import type { ReactionSummary } from "../api";
import styles from "../reactions.module.css";

/** Who reacted with what: everyone, one row each, the held emoji's people first. */
export function ReactorsSheet({
  open,
  onClose,
  summary,
  first,
  people,
  me,
}: {
  open: boolean;
  onClose: () => void;
  summary: ReactionSummary;
  /** The emoji whose chip was held: its people come first. */
  first: string | null;
  people: Map<string, Member>;
  me: string;
}) {
  const { t } = useTranslation();
  const groups = [...summary.groups].sort(
    (a, b) => Number(b.emoji === first) - Number(a.emoji === first),
  );
  const rows = groups.flatMap((group) =>
    group.member_ids.map((id) => ({ id, emoji: group.emoji })),
  );
  return (
    <Sheet
      open={open}
      onClose={onClose}
      title={t("reactions.count", { count: rows.length })}
      closeLabel={t("common.close")}
    >
      <List>
        {rows.map(({ id, emoji }) => {
          const member = people.get(id);
          const name = member?.display_name ?? "?";
          return (
            <ListRow
              key={id}
              leading={<Avatar name={name} seed={member?.avatar_seed ?? id} size="sm" />}
              title={id === me ? t("reactions.youName") : name}
              trailing={
                <span className={styles.emoji} role="img" aria-label={emoji}>
                  {emoji}
                </span>
              }
            />
          );
        })}
      </List>
    </Sheet>
  );
}
