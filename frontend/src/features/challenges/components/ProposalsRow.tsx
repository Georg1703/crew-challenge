import { useTranslation } from "react-i18next";

import { dayOfMonth, monthStart } from "@/shared/lib/dates";
import { monthName, todayIn } from "@/shared/lib/format";
import { Icon, IconTile, List, ListRow } from "@/shared/ui";

import { useChosenChallenges, usePool } from "../api";

/** Day of the month from which admins are reminded when next month has no challenge yet. */
const CHOOSE_REMINDER_DAY = 25;

/**
 * Crew tab: the pool as one slim row, only when there is something to do there: proposals
 * waiting for your vote, proposals in the list, or (admins, from the 25th) next month still
 * without a challenge.
 */
export function ProposalsRow({
  isAdmin,
  timeZone,
  now = new Date(),
}: {
  isAdmin: boolean;
  timeZone: string;
  now?: Date;
}) {
  const { t, i18n } = useTranslation();
  const pool = usePool();
  const upcoming = useChosenChallenges(["upcoming"], { enabled: isAdmin });
  if (!pool.data) return null;

  const today = todayIn(timeZone, now);
  const nextMonth = monthStart(today, 1);
  const remindAdmin =
    isAdmin &&
    dayOfMonth(today) >= CHOOSE_REMINDER_DAY &&
    upcoming.data !== undefined &&
    !upcoming.data.some((c) => c.period_kind === "month" && c.period_start === nextMonth);
  const waiting = pool.data.proposals.filter((p) => !p.my_vote).length;
  const size = pool.data.size;
  if (size === 0 && !remindAdmin) return null;

  const count =
    size === 0
      ? t("challenges.today.none")
      : waiting > 0
        ? t("challenges.today.waiting", { count: waiting })
        : t("challenges.today.listed", { count: size });
  return (
    <List label={t("challenges.today.label")}>
      <ListRow
        to={size === 0 ? "/challenges/new" : "/challenges"}
        leading={
          <IconTile tone="accent">
            <Icon name="star" size={20} />
          </IconTile>
        }
        title={
          remindAdmin
            ? t("challenges.today.chooseTitle", { month: monthName(nextMonth, i18n.language) })
            : count
        }
        subtitle={remindAdmin ? count : undefined}
      />
    </List>
  );
}
