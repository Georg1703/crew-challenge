import { useTranslation } from "react-i18next";
import { Outlet } from "react-router";

import { useMe } from "@/features/auth";
import { CheckInSheet, useCheckInAction } from "@/features/checkins";
import { TabBar } from "@/shared/ui";

export function AppShell() {
  const { t } = useTranslation();
  const me = useMe();
  const checkIn = useCheckInAction(Boolean(me.data?.member));
  return (
    <>
      <Outlet />
      <TabBar
        label={t("nav.label")}
        tabs={[
          { to: "/", label: t("nav.home"), icon: "sun", end: true },
          { to: "/crew", label: t("nav.crew"), icon: "users" },
          { to: "/me", label: t("nav.me"), icon: "user" },
        ]}
        action={checkIn.action}
      />
      {checkIn.open && <CheckInSheet onClose={checkIn.close} />}
    </>
  );
}
