import { useEffect } from "react";
import { useTranslation } from "react-i18next";

import { errorMessage } from "@/i18n/errors";
import { formatDateTime } from "@/shared/lib/format";
import { Button, Icon, Sheet, Skeleton, Stack, useToast } from "@/shared/ui";

import { useCreateInvite } from "../api";
import styles from "../crew.module.css";

/** Creates a fresh single-use invite when opened, then lets the admin copy or share it. */
export function InviteSheet({
  open,
  onClose,
  timeZone,
}: {
  open: boolean;
  onClose: () => void;
  timeZone: string;
}) {
  const { t, i18n } = useTranslation();
  const toast = useToast();
  const invite = useCreateInvite();
  const { mutate, reset } = invite;

  useEffect(() => {
    if (open) mutate();
    else reset();
  }, [open, mutate, reset]);

  const url = invite.data?.url;
  const canShare = typeof navigator.share === "function";

  const copy = async () => {
    if (!url) return;
    try {
      await navigator.clipboard.writeText(url);
      toast(t("common.copied"), "success");
    } catch {
      toast(t("common.somethingWrong"), "error");
    }
  };

  const share = () => {
    if (url) void navigator.share({ text: t("crew.shareText"), url }).catch(() => undefined);
  };

  return (
    <Sheet
      open={open}
      onClose={onClose}
      title={t("crew.inviteTitle")}
      closeLabel={t("common.close")}
    >
      <p className={styles.muted}>{t("crew.inviteBody")}</p>
      {invite.isPending && <Skeleton lines={2} />}
      {invite.isError && <p role="alert">{errorMessage(t, invite.error)}</p>}
      {invite.data && (
        <Stack>
          <output className={styles.link}>{invite.data.url}</output>
          <p className={styles.muted}>
            {t("crew.inviteExpires", {
              date: formatDateTime(invite.data.expires_at, i18n.language, timeZone),
            })}
          </p>
          <Button size="lg" fullWidth icon={<Icon name="copy" />} onClick={copy}>
            {t("crew.copyLink")}
          </Button>
          {canShare && (
            <Button variant="secondary" fullWidth icon={<Icon name="share" />} onClick={share}>
              {t("crew.shareLink")}
            </Button>
          )}
        </Stack>
      )}
    </Sheet>
  );
}
