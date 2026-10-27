import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Navigate, Outlet, useLocation, useSearchParams } from "react-router";

import { useMe, useOpenCrew } from "@/features/auth";
import { setLanguage } from "@/i18n";
import { Screen, Spinner } from "@/shared/ui";

import styles from "./app.module.css";

/**
 * Routes below need a session. Applies the user's saved language once they are known. A link
 * with `?crew=<id>` (a push notification) opens that crew first when it is another of theirs.
 */
export function RequireAuth() {
  const { t, i18n } = useTranslation();
  const location = useLocation();
  const [params, setParams] = useSearchParams();
  const me = useMe();
  const openCrew = useOpenCrew();
  const preferred = me.data?.user.preferred_language;
  const wanted = params.get("crew");
  const current = me.data?.crew?.id;
  const mine = me.data?.crews.some((crew) => crew.crew_id === wanted);

  useEffect(() => {
    if (preferred && preferred !== i18n.language) setLanguage(preferred);
  }, [preferred, i18n]);

  const open = openCrew.mutate;
  useEffect(() => {
    if (!wanted || !me.data) return;
    if (wanted !== current && mine) open(wanted);
    params.delete("crew");
    setParams(params, { replace: true });
  }, [wanted, current, mine, me.data, open, params, setParams]);

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
