import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";

import { Button, Card, Dial } from "@/shared/ui";

import { useSpins } from "../api";
import styles from "../doom.module.css";

/** On Today, under the day ring, while anything is owed: how much, and the way to the wheel. */
export function SpinsCard() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const owed = useSpins().data;
  const [first] = owed?.spins ?? [];
  if (!owed || !first) return null;
  const late = owed.spins.filter((spin) => spin.late).length;
  const title = [
    owed.to_spin > 0 && t("doom.toSpin", { count: owed.to_spin }),
    owed.to_serve > 0 && t("doom.toServe", { count: owed.to_serve }),
  ]
    .filter(Boolean)
    .join(" · ");
  return (
    <Card tone="accent">
      <div className={styles.stack}>
        <div className={styles.owed}>
          <Dial size="sm" count={first.punishments.length} label={t("doom.title")} />
          <div>
            <h2 className={styles.title}>{title}</h2>
            <p className={styles.meta}>
              {late ? t("doom.lateCount", { count: late }) : t("doom.cardBody")}
            </p>
          </div>
        </div>
        <Button onClick={() => navigate("/spins")}>{t("doom.open")}</Button>
      </div>
    </Card>
  );
}
