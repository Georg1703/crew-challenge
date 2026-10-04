import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";

import { errorMessage } from "@/i18n/errors";
import { formatDate } from "@/shared/lib/format";
import { Banner, Button, Icon, QrCode, Sheet, Skeleton, TextField, useToast } from "@/shared/ui";

import { useCreateInvite } from "../api";
import styles from "../crew.module.css";

/**
 * G15 Invite someone. Every time it opens it creates a new single-use link, so two people never
 * get the same one. QR code, link, copy and share.
 */
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
  const { mutate, reset, data: invite, error } = useCreateInvite();
  const created = useRef(false); // once per opening, also under React's double effects

  useEffect(() => {
    if (open && !created.current) {
      created.current = true;
      mutate();
    }
    if (!open) {
      created.current = false;
      reset();
    }
  }, [open, mutate, reset]);

  const copy = async () => {
    if (!invite) return;
    try {
      await navigator.clipboard.writeText(invite.url);
      toast(t("common.copied"), "success");
    } catch {
      toast(t("common.somethingWrong"), "error");
    }
  };

  const canShare = typeof navigator.share === "function";
  const share = () => {
    if (invite)
      void navigator.share({ text: t("crew.shareText"), url: invite.url }).catch(() => {});
  };

  return (
    <Sheet
      open={open}
      onClose={onClose}
      title={t("crew.inviteTitle")}
      closeLabel={t("common.close")}
    >
      <p className={styles.muted}>{t("crew.inviteBody")}</p>
      {error && <Banner tone="danger" title={errorMessage(t, error)} />}
      {!invite && !error && <Skeleton lines={3} />}
      {invite && (
        <>
          <QrCode value={invite.url} label={t("crew.qrLabel")} />
          <div className={styles.linkRow}>
            <TextField
              className={styles.linkField}
              label={t("crew.linkLabel")}
              value={invite.url}
              readOnly
              onFocus={(event) => event.target.select()}
            />
            <Button variant="secondary" icon={<Icon name="copy" size={20} />} onClick={copy}>
              {t("crew.copyLink")}
            </Button>
          </div>
          <p className={styles.muted}>
            {t("crew.inviteRule", { date: formatDate(invite.expires_at, i18n.language, timeZone) })}
          </p>
          {canShare && (
            <Button size="lg" fullWidth icon={<Icon name="share" size={20} />} onClick={share}>
              {t("crew.shareLink")}
            </Button>
          )}
        </>
      )}
    </Sheet>
  );
}
