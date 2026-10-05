import { useTranslation } from "react-i18next";

import type { Member } from "@/api";
import type { Today } from "@/features/checkins";
import { Avatar, List, ListRow, StatusPill } from "@/shared/ui";

type CrewDay = Today["crew"][number];

/** Members in the order they joined; who has something due today gets the today ring and "2 of 3". */
export function MemberList({
  members,
  meId,
  today = [],
}: {
  members: Member[];
  meId?: string;
  today?: CrewDay[];
}) {
  const { t } = useTranslation();
  const byMember = new Map(today.map((row) => [row.member.id, row]));
  return (
    <List label={t("crew.membersLabel")}>
      {members.map((member) => {
        const role = member.role === "admin" ? t("crew.admin") : t("crew.member");
        const day = byMember.get(member.id);
        const due = day !== undefined && day.needed > 0;
        const counts = due ? { done: day.done, needed: day.needed } : undefined;
        return (
          <ListRow
            key={member.id}
            leading={
              <Avatar
                name={member.display_name}
                seed={member.avatar_seed}
                ring={counts && (counts.done >= counts.needed ? "done" : "todo")}
                label={counts && t("crew.todayRow", { name: member.display_name, ...counts })}
              />
            }
            title={member.display_name}
            subtitle={counts ? t("crew.todaySubtitle", { role, ...counts }) : role}
            trailing={member.id === meId && <StatusPill tone="accent">{t("crew.you")}</StatusPill>}
          />
        );
      })}
    </List>
  );
}
