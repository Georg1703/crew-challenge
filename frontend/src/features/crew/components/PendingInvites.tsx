import { useState } from "react";
import { useTranslation } from "react-i18next";

import type { PendingInvite } from "@/api";
import { errorMessage } from "@/i18n/errors";
import { formatDate } from "@/shared/lib/format";
import { Button, Icon, IconTile, List, ListRow, Sheet, useToast } from "@/shared/ui";

import { usePendingInvites, useRevokeInvite } from "../api";
import styles from "../crew.module.css";

/** Admins: invites nobody has used yet, each with Cancel (confirmed in a sheet). */
export function PendingInvites({ timeZone }: { timeZone: string }) {
  const { t, i18n } = useTranslation();
  const toast = useToast();
  const pending = usePendingInvites();
  const revoke = useRevokeInvite();
  const [confirming, setConfirming] = useState<PendingInvite | null>(null);

  if (!pending.data?.length) return null;

  const confirm = () => {
    if (!confirming) return;
    revoke.mutate(confirming, {
      onSuccess: () => toast(t("crew.revoked"), "success"),
      onError: (error) => toast(errorMessage(t, error), "error"),
    });
    setConfirming(null);
  };

  return (
    <section className={styles.section}>
      <h2 className={styles.sectionTitle}>{t("crew.pendingTitle")}</h2>
      <List label={t("crew.pendingLabel")}>
        {pending.data.map((invite) => (
          <ListRow
            key={invite.id}
            leading={
              <IconTile>
                <Icon name="link" size={20} />
              </IconTile>
            }
            title={t("crew.pendingRow", { code: invite.code.toUpperCase() })}
            subtitle={t("crew.pendingExpires", {
              date: formatDate(invite.expires_at, i18n.language, timeZone),
            })}
            trailing={
              <Button variant="ghost" onClick={() => setConfirming(invite)}>
                {t("crew.revoke")}
              </Button>
            }
          />
        ))}
      </List>
      <Sheet
        open={confirming !== null}
        onClose={() => setConfirming(null)}
        title={t("crew.revokeTitle")}
        closeLabel={t("common.close")}
      >
        <p className={styles.muted}>
          {t("crew.revokeBody", { code: confirming?.code.toUpperCase() ?? "" })}
        </p>
        <div className={styles.actions}>
          <Button variant="danger" size="lg" fullWidth onClick={confirm}>
            {t("crew.revokeConfirm")}
          </Button>
          <Button variant="secondary" size="lg" fullWidth onClick={() => setConfirming(null)}>
            {t("crew.revokeKeep")}
          </Button>
        </div>
      </Sheet>
    </section>
  );
}
