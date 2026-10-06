import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { Card, Icon, ProgressRing, type RingSegment } from "@/shared/ui";

import type { Today } from "../api";
import styles from "../checkins.module.css";

/** From this many minutes before midnight, unfinished days show how long is left. */
const DEADLINE_WARNING_MINUTES = 4 * 60;

function useNow(): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), 60_000);
    return () => window.clearInterval(id);
  }, []);
  return now;
}

/** Today's ring: a segment per challenge that asks for something today. */
export function DayRing({ today }: { today: Today }) {
  const { t } = useTranslation();
  const now = useNow();
  const segments: RingSegment[] = today.challenges
    .filter((c) => c.settled !== null)
    .map((c) => (c.settled ? "full" : c.state === "partial" ? "partial" : "empty"));
  const done = segments.filter((s) => s === "full").length;
  const left = Math.max(0, Math.floor((Date.parse(today.deadline) - now) / 60_000));
  const late = segments.length > done && left <= DEADLINE_WARNING_MINUTES;

  if (segments.length === 0) {
    return (
      <Card>
        <h2 className={styles.cardTitle}>{t("checkins.restTitle")}</h2>
        <p className={styles.muted}>{t("checkins.restBody")}</p>
      </Card>
    );
  }
  return (
    <Card className={styles.ringCard}>
      <ProgressRing
        segments={segments}
        label={t("checkins.ringLabel", { done, total: segments.length })}
        done={
          <>
            <Icon name="check" size={32} />
            <span className={styles.ringCaption}>{t("checkins.dayDone")}</span>
          </>
        }
      >
        <span className={styles.ringNumber}>
          {t("checkins.fraction", { done, total: segments.length })}
        </span>
        <span className={styles.ringCaption}>{t("checkins.today")}</span>
      </ProgressRing>
      {late && (
        <p className={styles.deadline}>
          {t("checkins.timeLeft", { h: Math.floor(left / 60), m: left % 60 })}
        </p>
      )}
    </Card>
  );
}
