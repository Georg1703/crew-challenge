import { useTranslation } from "react-i18next";

import { Banner, Button } from "@/shared/ui";

import { usePwaUpdate } from "./usePwaUpdate";

/** "A new version is ready" - shown on every screen until the user updates or postpones. */
export function UpdateBanner() {
  const { t } = useTranslation();
  const { needRefresh, update, later } = usePwaUpdate();
  return (
    <Banner
      open={needRefresh}
      floating
      title={t("pwa.updateReady")}
      actions={
        <>
          <Button variant="ghost" onClick={later}>
            {t("pwa.later")}
          </Button>
          <Button onClick={() => void update()}>{t("pwa.update")}</Button>
        </>
      }
    />
  );
}
