import { useTranslation } from "react-i18next";

import type { Member } from "@/api";
import { Avatar, List, ListRow, StatusPill } from "@/shared/ui";

/** Members in rotation order, in one list. */
export function MemberList({ members, meId }: { members: Member[]; meId?: string }) {
  const { t } = useTranslation();
  return (
    <List label={t("crew.membersLabel")}>
      {members.map((member) => (
        <ListRow
          key={member.id}
          leading={<Avatar name={member.display_name} seed={member.avatar_seed} />}
          title={member.display_name}
          subtitle={member.role === "admin" ? t("crew.admin") : t("crew.member")}
          trailing={member.id === meId && <StatusPill tone="accent">{t("crew.you")}</StatusPill>}
        />
      ))}
    </List>
  );
}
