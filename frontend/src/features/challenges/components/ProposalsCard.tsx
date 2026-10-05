import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";

import { monthName, todayIn } from "@/shared/lib/format";
import { Button, Card, Skeleton } from "@/shared/ui";

import { useChosenChallenges, usePool } from "../api";
import styles from "../challenges.module.css";
import { monthStart } from "../months";

/** Day of the month from which admins are reminded when next month has no challenge yet. */
const CHOOSE_REMINDER_DAY = 25;

/** Crew tab: the pool at a glance (propose, vote), and the admin's reminder from the 25th. */
export function ProposalsCard({
  isAdmin,
  timeZone,
  now = new Date(),
}: {
  isAdmin: boolean;
  timeZone: string;
  now?: Date;
}) {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const pool = usePool();
  const upcoming = useChosenChallenges(["upcoming"], { enabled: isAdmin });

  if (pool.isPending) return <Skeleton lines={2} />;
  if (!pool.data) return null;

  const today = todayIn(timeZone, now);
  const nextMonth = monthStart(today, 1);
  const remindAdmin =
    isAdmin &&
    Number(today.slice(8, 10)) >= CHOOSE_REMINDER_DAY &&
    upcoming.data !== undefined &&
    !upcoming.data.some((c) => c.period_start === nextMonth);
  const proposals = pool.data.size;

  return (
    <Card tone="accent">
      <h2 className={styles.cardTitle}>
        {remindAdmin
          ? t("challenges.today.chooseTitle", { month: monthName(nextMonth, i18n.language) })
          : t("challenges.today.poolTitle")}
      </h2>
      <p className={styles.muted}>
        {proposals === 0
          ? t("challenges.today.none")
          : proposals === 1
            ? t("challenges.today.one")
            : t("challenges.today.some", { n: proposals })}
      </p>
      <Button onClick={() => navigate(proposals ? "/challenges" : "/challenges/new")}>
        {proposals ? t("challenges.today.see") : t("challenges.propose")}
      </Button>
    </Card>
  );
}
