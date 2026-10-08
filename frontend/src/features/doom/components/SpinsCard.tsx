import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { Card, Dial, Icon } from "@/shared/ui";

import { useSpins } from "../api";
import styles from "../doom.module.css";

const MARK_SEGMENTS = 6; // the mark is a sign, not this challenge's punishments: six reads best

/** On Today, under the day ring, while anything is owed: how much. The whole card opens the wheel. */
export function SpinsCard() {
  const { t } = useTranslation();
  const owed = useSpins().data;
  if (!owed?.spins.length) return null;
  const late = owed.spins.filter((spin) => spin.late).length;
  const title = [
    owed.to_spin > 0 && t("doom.toSpin", { count: owed.to_spin }),
    owed.to_serve > 0 && t("doom.toServe", { count: owed.to_serve }),
  ]
    .filter(Boolean)
    .join(" · ");
  return (
    <Card tone="accent">
      <Link to="/spins" className={styles.owed}>
        <Dial size="sm" count={MARK_SEGMENTS} label={t("doom.title")}>
          <span className={styles.markCount} aria-hidden="true">
            {owed.spins.length}
          </span>
        </Dial>
        <div className={styles.owedText}>
          <h2 className={styles.title}>{title}</h2>
          <p className={styles.meta}>
            {late ? t("doom.lateCount", { count: late }) : t("doom.cardBody")}
          </p>
        </div>
        <Icon name="chevronRight" size={20} />
      </Link>
    </Card>
  );
}
