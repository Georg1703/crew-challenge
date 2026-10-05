import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";

import { formatDay, monthName, todayIn } from "@/shared/lib/format";
import { Button, Card, Skeleton } from "@/shared/ui";

import { useChosenChallenges, usePool } from "../api";
import styles from "../challenges.module.css";
import { summaryLine } from "../describe";
import { monthStart } from "../months";
import { ChallengeRows } from "./ChallengeRows";

/** Day of the month from which admins are reminded when next month has no challenge yet. */
const CHOOSE_REMINDER_DAY = 25;

/** Today: the running challenges, the upcoming ones, and the pool (propose, vote, choose). */
export function TodayChallenges({
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
  const chosen = useChosenChallenges(["active", "upcoming"]);

  if (pool.isPending || chosen.isPending) return <Skeleton lines={3} />;

  const active = chosen.data?.filter((c) => c.phase === "active") ?? [];
  const upcoming = chosen.data?.filter((c) => c.phase === "upcoming") ?? [];
  const today = todayIn(timeZone, now);
  const nextMonth = monthStart(today, 1);
  const nextMonthEmpty = !upcoming.some((c) => c.period_start === nextMonth);
  const remindAdmin =
    isAdmin && nextMonthEmpty && Number(today.slice(8, 10)) >= CHOOSE_REMINDER_DAY;
  const proposals = pool.data?.size ?? 0;

  return (
    <>
      {active.map((challenge) => (
        <Card key={challenge.id}>
          <h2 className={styles.cardTitle}>{challenge.title}</h2>
          <p className={styles.meta}>{summaryLine(t, challenge, i18n.language)}</p>
          {challenge.end_date && (
            <p className={styles.meta}>
              {t("challenges.until", { date: formatDay(challenge.end_date, i18n.language) })}
            </p>
          )}
          <Button variant="secondary" onClick={() => navigate(`/challenges/${challenge.id}`)}>
            {t("challenges.open")}
          </Button>
        </Card>
      ))}
      {active.length === 0 && upcoming.length === 0 && (
        <Card>
          <h2 className={styles.cardTitle}>{t("home.noChallengeTitle")}</h2>
          <p className={styles.muted}>{t("home.noChallengeBody")}</p>
        </Card>
      )}
      {upcoming.length > 0 && (
        <ChallengeRows challenges={upcoming} label={t("challenges.sections.upcoming")} />
      )}
      {pool.data && (
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
      )}
    </>
  );
}
