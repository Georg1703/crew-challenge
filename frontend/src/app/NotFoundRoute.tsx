import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { Card, Screen } from "@/shared/ui";

import styles from "./app.module.css";

export function NotFoundRoute() {
  const { t } = useTranslation();
  return (
    <Screen withTabBar={false}>
      <Card>
        <h1 className={styles.title}>{t("notFound.title")}</h1>
        <Link className={styles.link} to="/">
          {t("notFound.back")}
        </Link>
      </Card>
    </Screen>
  );
}
