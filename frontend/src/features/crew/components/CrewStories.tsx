import { useTranslation } from "react-i18next";

import type { Member } from "@/api";
import type { Today } from "@/features/checkins";
import { StoryAvatar, type StorySegment } from "@/shared/ui";

import styles from "../crew.module.css";

type CrewDay = Today["crew"][number];

const NOTHING_DUE = "-";

/**
 * Everyone's day at a glance: a ring per member split by today's challenges, you first, then
 * whoever has done the most, then in join order. Someone with nothing due gets a plain ring.
 */
export function CrewStories({
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
  const share = (m: Member) => {
    const day = byMember.get(m.id);
    return day && day.needed > 0 ? day.done / day.needed : -1;
  };
  const ordered = members
    .map((member, index) => ({ member, index }))
    .sort(
      (a, b) =>
        Number(b.member.id === meId) - Number(a.member.id === meId) ||
        share(b.member) - share(a.member) ||
        a.index - b.index,
    )
    .map(({ member }) => member);

  return (
    <ul className={styles.stories} aria-label={t("crew.journal.storiesLabel")}>
      {ordered.map((member) => {
        const day = byMember.get(member.id);
        const due = day !== undefined && day.needed > 0;
        const name = member.display_name;
        const segments: StorySegment[] = day?.challenges.map((c) => c.state) ?? [];
        return (
          <li key={member.id} className={styles.story}>
            <StoryAvatar
              name={name}
              seed={member.avatar_seed}
              segments={segments}
              title={member.id === meId ? t("crew.journal.you") : name}
              subtitle={due ? `${day.done}/${day.needed}` : NOTHING_DUE}
              complete={due && day.done >= day.needed}
              label={
                due
                  ? t("crew.todayRow", { name, done: day.done, needed: day.needed })
                  : t("crew.journal.nothingDue", { name })
              }
            />
          </li>
        );
      })}
    </ul>
  );
}
