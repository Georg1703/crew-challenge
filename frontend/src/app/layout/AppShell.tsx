import { useTranslation } from "react-i18next";
import { Outlet } from "react-router";

import { TabBar } from "@/shared/ui";

export function AppShell() {
  const { t } = useTranslation();
  return (
    <>
      <Outlet />
      <TabBar
        label={t("nav.label")}
        tabs={[
          { to: "/", label: t("nav.home"), icon: "home", end: true },
          { to: "/crew", label: t("nav.crew"), icon: "crew" },
          { to: "/me", label: t("nav.me"), icon: "me" },
        ]}
      />
    </>
  );
}
