import { useState } from "react";
import { useTranslation } from "react-i18next";

import { useMe } from "@/features/auth";
import { useToday } from "@/features/checkins";
import { errorMessage } from "@/i18n/errors";
import { Banner, Button, Icon, Screen, Skeleton } from "@/shared/ui";

import { useCrew } from "../api";
import { InviteSheet } from "../components/InviteSheet";
import { MemberList } from "../components/MemberList";
import { PendingInvites } from "../components/PendingInvites";

/** Everyone in the crew with their role and day; admins invite and see the invites they sent. */
export function MembersRoute() {
  const { t } = useTranslation();
  const me = useMe();
  const crew = useCrew();
  const today = useToday();
  const [inviting, setInviting] = useState(false);
  const isAdmin = me.data?.member?.role === "admin";

  return (
    <Screen title={t("crew.members.title")}>
      {crew.isPending && <Skeleton lines={4} />}
      {crew.isError && <Banner tone="danger" title={errorMessage(t, crew.error)} />}
      {crew.data && (
        <>
          <MemberList
            members={crew.data.members}
            meId={me.data?.member?.id}
            today={today.data?.crew}
          />
          {isAdmin && (
            <>
              <Button
                variant="secondary"
                size="lg"
                fullWidth
                icon={<Icon name="userPlus" size={20} />}
                onClick={() => setInviting(true)}
              >
                {t("crew.invite")}
              </Button>
              <PendingInvites timeZone={crew.data.timezone} />
              <InviteSheet
                open={inviting}
                onClose={() => setInviting(false)}
                timeZone={crew.data.timezone}
              />
            </>
          )}
        </>
      )}
    </Screen>
  );
}
