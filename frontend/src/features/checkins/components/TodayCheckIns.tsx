import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { errorMessage } from "@/i18n/errors";
import { Banner, Card, Skeleton } from "@/shared/ui";

import { useToday } from "../api";
import styles from "../checkins.module.css";
import { CheckInCard } from "./CheckInCard";
import { DayRing } from "./DayRing";

/**
 * Today: the day ring and a card per challenge to check in. The crew's day is on Echipa.
 * `afterRing` goes right under the ring (on top when there is no challenge today).
 */
export function TodayCheckIns({ afterRing }: { afterRing?: ReactNode }) {
  const { t } = useTranslation();
  const today = useToday();

  if (today.isPending) return <Skeleton lines={4} />;
  if (today.error) return <Banner tone="danger" title={errorMessage(t, today.error)} />;

  const { challenges, day } = today.data;
  if (challenges.length === 0) {
    return (
      <div className={styles.stack}>
        {afterRing}
        <Card>
          <h2 className={styles.cardTitle}>{t("home.noChallengeTitle")}</h2>
          <p className={styles.muted}>{t("home.noChallengeBody")}</p>
        </Card>
      </div>
    );
  }
  return (
    <div className={styles.stack}>
      <DayRing today={today.data} />
      {afterRing}
      {challenges.map((card) => (
        <CheckInCard key={card.id} card={card} day={day} linked />
      ))}
    </div>
  );
}
