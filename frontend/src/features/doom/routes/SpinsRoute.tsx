import { useTranslation } from "react-i18next";

import { errorMessage } from "@/i18n/errors";
import { Banner, Card, Screen, Skeleton } from "@/shared/ui";

import { useSpins } from "../api";
import { SpinCard } from "../components/SpinCard";
import styles from "../doom.module.css";

/** /spins: one card per spin not served yet, oldest first. */
export function SpinsRoute() {
  const { t } = useTranslation();
  const spins = useSpins();
  const owed = spins.data;

  return (
    <Screen title={t("doom.title")}>
      {spins.isPending && <Skeleton lines={5} />}
      {spins.error && <Banner tone="danger" title={errorMessage(t, spins.error)} />}
      {owed && owed.spins.length === 0 && (
        <Card>
          <h2 className={styles.title}>{t("doom.emptyTitle")}</h2>
          <p className={styles.muted}>{t("doom.emptyBody")}</p>
        </Card>
      )}
      {owed && owed.spins.length > 0 && (
        <div className={styles.stack}>
          {owed.spins.map((spin) => (
            <SpinCard key={spin.id} spin={spin} />
          ))}
        </div>
      )}
    </Screen>
  );
}
