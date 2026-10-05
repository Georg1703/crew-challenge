import { useTranslation } from "react-i18next";

import { errorMessage } from "@/i18n/errors";
import { Banner, Card, Skeleton } from "@/shared/ui";

import { useToday } from "../api";
import styles from "../checkins.module.css";
import { CheckInCard } from "./CheckInCard";
import { CrewToday } from "./CrewToday";
import { DayRing } from "./DayRing";

/** Today: the day ring, a card per challenge to check in, and the crew's day. */
export function TodayCheckIns({ meId }: { meId?: string }) {
  const { t } = useTranslation();
  const today = useToday();

  if (today.isPending) return <Skeleton lines={4} />;
  if (today.error) return <Banner tone="danger" title={errorMessage(t, today.error)} />;

  const { challenges, crew, day } = today.data;
  if (challenges.length === 0) {
    return (
      <div className={styles.stack}>
        <Card>
          <h2 className={styles.cardTitle}>{t("home.noChallengeTitle")}</h2>
          <p className={styles.muted}>{t("home.noChallengeBody")}</p>
        </Card>
        <CrewToday crew={crew} meId={meId} />
      </div>
    );
  }
  return (
    <div className={styles.stack}>
      <DayRing today={today.data} />
      {challenges.map((card) => (
        <CheckInCard key={card.id} card={card} day={day} />
      ))}
      <CrewToday crew={crew} meId={meId} />
    </div>
  );
}
