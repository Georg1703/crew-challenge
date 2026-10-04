import { useTranslation } from "react-i18next";

import { formatDay } from "@/shared/lib/format";
import { List, ListRow } from "@/shared/ui";

import type { Challenge } from "../api";
import { ChallengeIcon } from "./ChallengeIcon";
import { PhasePill } from "./PhasePill";

/** Chosen challenges as rows: icon, title, dates, phase. */
export function ChallengeRows({ challenges, label }: { challenges: Challenge[]; label: string }) {
  const { t, i18n } = useTranslation();
  return (
    <List label={label}>
      {challenges.map((challenge) => (
        <ListRow
          key={challenge.id}
          to={`/challenges/${challenge.id}`}
          leading={<ChallengeIcon icon={challenge.icon} />}
          title={challenge.title}
          subtitle={
            challenge.start_date && challenge.end_date
              ? t("challenges.dates", {
                  start: formatDay(challenge.start_date, i18n.language),
                  end: formatDay(challenge.end_date, i18n.language),
                })
              : undefined
          }
          trailing={<PhasePill challenge={challenge} />}
        />
      ))}
    </List>
  );
}
