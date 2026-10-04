import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Navigate, Outlet, useLocation } from "react-router";

import { useMe } from "@/features/auth";
import { setLanguage } from "@/i18n";
import { Screen, Spinner } from "@/shared/ui";

import styles from "./app.module.css";

/** Routes below need a session. Applies the user's saved language once they are known. */
export function RequireAuth() {
  const { t, i18n } = useTranslation();
  const location = useLocation();
  const me = useMe();
  const preferred = me.data?.user.preferred_language;

  useEffect(() => {
    if (preferred && preferred !== i18n.language) setLanguage(preferred);
  }, [preferred, i18n]);

  if (me.isPending) {
    return (
      <Screen withTabBar={false}>
        <div className={styles.center}>
          <Spinner label={t("common.loading")} />
        </div>
      </Screen>
    );
  }
  if (!me.data) {
    const next = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/login?next=${next}`} replace />;
  }
  return <Outlet />;
}
