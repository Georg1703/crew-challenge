import { useTranslation } from "react-i18next";

import { Icon, Sheet, Skeleton } from "@/shared/ui";

import { useToday } from "../api";
import styles from "../checkins.module.css";
import { CheckInCard } from "./CheckInCard";

/** What is still left today, ready to check in: everything (the raised tab button) or one challenge. */
export function CheckInSheet({
  onClose,
  challengeId,
}: {
  onClose: () => void;
  challengeId?: string;
}) {
  const { t } = useTranslation();
  const today = useToday();
  const left = today.data?.challenges.filter(
    (c) =>
      (c.settled === false || c.state === "partial") &&
      (challengeId === undefined || c.id === challengeId),
  );

  return (
    <Sheet open onClose={onClose} title={t("checkins.sheetTitle")} closeLabel={t("common.close")}>
      {!today.data && <Skeleton lines={3} />}
      {left && left.length === 0 && (
        <div className={styles.allDone}>
          <Icon name="check" size={32} />
          <p className={styles.cardTitle}>{t("checkins.dayDone")}</p>
        </div>
      )}
      {left && left.length > 0 && today.data && (
        <div className={styles.stack}>
          {left.map((card) => (
            <CheckInCard key={card.id} card={card} day={today.data.day} />
          ))}
        </div>
      )}
    </Sheet>
  );
}
