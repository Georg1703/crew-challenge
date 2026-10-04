import { useState } from "react";
import { useTranslation } from "react-i18next";

import { useMe } from "@/features/auth";
import { errorMessage } from "@/i18n/errors";
import { Button, Card, Icon, Screen, Skeleton } from "@/shared/ui";

import { useCrew } from "../api";
import { InviteSheet } from "../components/InviteSheet";
import { MemberList } from "../components/MemberList";
import styles from "../crew.module.css";

export function CrewRoute() {
  const { t } = useTranslation();
  const me = useMe();
  const crew = useCrew();
  const [inviting, setInviting] = useState(false);
  const isAdmin = me.data?.member?.role === "admin";

  return (
    <Screen
      title={crew.data?.name ?? t("crew.title")}
      action={
        isAdmin && (
          <Button size="md" icon={<Icon name="plus" />} onClick={() => setInviting(true)}>
            {t("crew.invite")}
          </Button>
        )
      }
    >
      {crew.isPending && <Skeleton lines={4} />}
      {crew.isError && (
        <Card>
          <p role="alert">{errorMessage(t, crew.error)}</p>
          <Button variant="secondary" onClick={() => void crew.refetch()}>
            {t("common.retry")}
          </Button>
        </Card>
      )}
      {crew.data && (
        <>
          <p className={styles.muted}>{t("crew.rotationHint")}</p>
          <MemberList members={crew.data.members} meId={me.data?.member?.id} />
          <InviteSheet
            open={inviting}
            onClose={() => setInviting(false)}
            timeZone={crew.data.timezone}
          />
        </>
      )}
    </Screen>
  );
}
