import { useTranslation } from "react-i18next";

import { errorMessage } from "@/i18n/errors";
import { Banner, Card, Skeleton } from "@/shared/ui";

import { useToday } from "../api";
import styles from "../checkins.module.css";
import { CheckInCard } from "./CheckInCard";
import { DayRing } from "./DayRing";

/** Today: the day ring and a card per challenge to check in. The crew's day is on Echipa. */
export function TodayCheckIns() {
  const { t } = useTranslation();
  const today = useToday();

  if (today.isPending) return <Skeleton lines={4} />;
  if (today.error) return <Banner tone="danger" title={errorMessage(t, today.error)} />;

  const { challenges, day } = today.data;
  if (challenges.length === 0) {
    return (
      <Card>
        <h2 className={styles.cardTitle}>{t("home.noChallengeTitle")}</h2>
        <p className={styles.muted}>{t("home.noChallengeBody")}</p>
      </Card>
    );
  }
  return (
    <div className={styles.stack}>
      <DayRing today={today.data} />
      {challenges.map((card) => (
        <CheckInCard key={card.id} card={card} day={day} />
      ))}
    </div>
  );
}
