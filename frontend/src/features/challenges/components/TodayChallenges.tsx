import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";

import { formatDay, monthName } from "@/shared/lib/format";
import { Button, Card, Skeleton } from "@/shared/ui";

import { useChosenChallenges, useCurrentRound } from "../api";
import styles from "../challenges.module.css";
import { summaryLine } from "../describe";
import { ChallengeRows } from "./ChallengeRows";

/** Day of the month from which admins are reminded to choose next month's challenge. */
const CHOOSE_REMINDER_DAY = 25;

/** Today: the running and upcoming challenges, and next month's round (propose, vote, choose). */
export function TodayChallenges({ isAdmin, today }: { isAdmin: boolean; today: Date }) {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const round = useCurrentRound();
  const chosen = useChosenChallenges(["active", "upcoming"]);

  if (round.isPending || chosen.isPending) return <Skeleton lines={3} />;

  const active = chosen.data?.filter((c) => c.phase === "active") ?? [];
  const upcoming = chosen.data?.filter((c) => c.phase === "upcoming") ?? [];
  const month = round.data ? monthName(round.data.period_start, i18n.language) : "";
  const proposals = round.data?.proposals.length ?? 0;
  const remindAdmin = isAdmin && proposals > 0 && today.getDate() >= CHOOSE_REMINDER_DAY;

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
      {round.data && (
        <Card tone="accent">
          <h2 className={styles.cardTitle}>
            {remindAdmin
              ? t("challenges.today.chooseTitle", { month })
              : t("challenges.today.roundTitle", { month })}
          </h2>
          <p className={styles.muted}>
            {proposals === 0
              ? t("challenges.today.none", { month })
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
