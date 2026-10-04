import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";

import { isApiError } from "@/api";
import { useLogout, useMe } from "@/features/auth";
import { setLanguage, type Language } from "@/i18n";
import { InstallCard } from "@/pwa";
import { errorMessage } from "@/i18n/errors";
import {
  Avatar,
  Button,
  Card,
  Icon,
  Screen,
  Segmented,
  Stack,
  TextField,
  useToast,
} from "@/shared/ui";

import { useUpdateMe } from "../api";
import styles from "../me.module.css";

export function MeRoute() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const toast = useToast();
  const me = useMe();
  const update = useUpdateMe();
  const logout = useLogout();
  const member = me.data?.member;
  const [name, setName] = useState(member?.display_name ?? "");

  const saveName = (event: FormEvent) => {
    event.preventDefault();
    update.mutate({ display_name: name }, { onSuccess: () => toast(t("common.saved"), "success") });
  };

  const changeLanguage = (language: Language) => {
    setLanguage(language);
    update.mutate({ preferred_language: language });
  };

  const nameError =
    isApiError(update.error) && update.variables?.display_name !== undefined
      ? (update.error.field("display_name") ?? errorMessage(t, update.error))
      : undefined;

  return (
    <Screen title={t("me.title")}>
      {member && (
        <Card>
          <div className={styles.profile}>
            <Avatar name={member.display_name} seed={member.avatar_seed} size="lg" />
            <div>
              <p className={styles.name}>{member.display_name}</p>
              <p className={styles.muted}>{me.data?.user.username}</p>
            </div>
          </div>
          <form onSubmit={saveName}>
            <Stack gap="sm">
              <TextField
                label={t("me.displayName")}
                name="display_name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                error={nameError}
              />
              <Button
                type="submit"
                variant="secondary"
                loading={update.isPending && update.variables?.display_name !== undefined}
                disabled={!name.trim() || name === member.display_name}
              >
                {t("common.save")}
              </Button>
            </Stack>
          </form>
        </Card>
      )}
      <Card>
        <Segmented<Language>
          label={t("me.language")}
          value={i18n.language === "en" ? "en" : "ro"}
          onChange={changeLanguage}
          options={[
            { value: "ro", label: t("languages.ro") },
            { value: "en", label: t("languages.en") },
          ]}
        />
      </Card>
      <InstallCard />
      <Button
        variant="danger"
        fullWidth
        icon={<Icon name="logout" />}
        loading={logout.isPending}
        onClick={() => logout.mutate(undefined, { onSettled: () => navigate("/login") })}
      >
        {t("me.logout")}
      </Button>
    </Screen>
  );
}
