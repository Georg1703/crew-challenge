import { useTranslation } from "react-i18next";
import { Outlet } from "react-router";

import { useMe } from "@/features/auth";
import { CheckInSheet, useCheckInAction } from "@/features/checkins";
import { useUnreadCount } from "@/features/comments";
import { useMediaSession } from "@/features/proofs";
import { TabBar } from "@/shared/ui";

export function AppShell() {
  const { t } = useTranslation();
  const me = useMe();
  const checkIn = useCheckInAction(Boolean(me.data?.member));
  const unread = useUnreadCount(Boolean(me.data?.member)).data ?? 0;
  useMediaSession(me.data?.member?.id);
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
            badge: { count: unread, label: t("comments.badge", { count: unread }) },
          },
          { to: "/me", label: t("nav.me"), icon: "user" },
        ]}
        action={checkIn.action}
      />
      {checkIn.open && <CheckInSheet onClose={checkIn.close} />}
    </>
  );
}
