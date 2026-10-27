import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Outlet } from "react-router";

import { useMe } from "@/features/auth";
import { CheckInSheet, useCheckInAction } from "@/features/checkins";
import { renewPush, useNews } from "@/features/notifications";
import { useMediaSession } from "@/features/proofs";
import { TabBar } from "@/shared/ui";

export function AppShell() {
  const { t } = useTranslation();
  const me = useMe();
  const checkIn = useCheckInAction(Boolean(me.data?.member));
  const memberId = me.data?.member?.id;
  const unread = useNews(Boolean(memberId)).data?.unread ?? 0;
  useMediaSession(memberId);
  useEffect(() => {
    if (memberId) void renewPush(); // browsers renew push endpoints: the server keeps the latest
  }, [memberId]);
  return (
    <>
      <Outlet />
      <TabBar
        label={t("nav.label")}
        tabs={[
          { to: "/", label: t("nav.home"), icon: "sun", end: true },
          {
            to: "/crew",
            label: t("nav.crew"),
            icon: "users",
            badge: { count: unread, label: t("news.badge", { count: unread }) },
          },
          { to: "/me", label: t("nav.me"), icon: "user" },
        ]}
        action={checkIn.action}
      />
      {checkIn.open && <CheckInSheet onClose={checkIn.close} />}
    </>
  );
}
