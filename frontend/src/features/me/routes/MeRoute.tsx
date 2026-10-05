import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";

import { isApiError } from "@/api";
import { useLogout, useMe } from "@/features/auth";
import { setLanguage, type Language } from "@/i18n";
import { InstallCard } from "@/pwa";
import { errorMessage } from "@/i18n/errors";
import { setTheme, storedTheme, type Theme } from "@/shared/lib/theme";
import {
  Avatar,
  Button,
  Card,
  Icon,
  IconTile,
  List,
  ListRow,
  Screen,
  Segmented,
  Skeleton,
  Stack,
  StatusPill,
  TextField,
  useToast,
} from "@/shared/ui";

import { useSwitchCrew, useUpdateMe } from "../api";
import styles from "../me.module.css";

/** Me: profile, crews (when you are in several), language and theme, install, log out. */
export function MeRoute() {
  const { t } = useTranslation();
  const me = useMe();
  if (me.isPending) {
    return (
      <Screen title={t("me.title")}>
        <Skeleton lines={4} />
      </Screen>
    );
  }
  // A new crew means a new display name: remount the form so it starts from the right value.
  return <MeScreen key={me.data?.member?.id ?? "none"} />;
}

function MeScreen() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const toast = useToast();
  const me = useMe();
  const update = useUpdateMe();
  const logout = useLogout();
  const switchCrew = useSwitchCrew();
  const member = me.data?.member;
  const crews = me.data?.crews ?? [];
  const [name, setName] = useState(member?.display_name ?? "");
  const [theme, setThemeState] = useState<Theme>(storedTheme);

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
                maxLength={40}
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
      <List label={t("me.moreLabel")}>
        <ListRow
          to="/challenges"
          leading={
            <IconTile>
              <Icon name="flag" size={20} />
            </IconTile>
          }
          title={t("challenges.title")}
          subtitle={t("me.challengesHint")}
          trailing={<Icon name="chevronRight" size={20} />}
        />
      </List>
      {crews.length > 1 && (
        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>{t("me.crewsTitle")}</h2>
          <List label={t("me.crewsTitle")}>
            {crews.map((crew) => {
              const current = crew.crew_id === me.data?.crew?.id;
              return (
                <ListRow
                  key={crew.crew_id}
                  current={current}
                  leading={
                    <IconTile tone={current ? "accent" : "neutral"}>
                      <Icon name="users" size={20} />
                    </IconTile>
                  }
                  title={crew.crew_name}
                  subtitle={t("me.crewAs", { name: crew.display_name })}
                  trailing={
                    current ? (
                      <StatusPill tone="success">{t("me.crewCurrent")}</StatusPill>
                    ) : (
                      <Icon name="chevronRight" size={20} />
                    )
                  }
                  onClick={
                    current || switchCrew.isPending
                      ? undefined
                      : () =>
                          switchCrew.mutate(crew.crew_id, {
                            onSuccess: () =>
                              toast(t("me.crewSwitched", { crew: crew.crew_name }), "success"),
                            onError: (error) => toast(errorMessage(t, error), "error"),
                          })
                  }
                />
              );
            })}
          </List>
        </section>
      )}
      <Card>
        <Stack>
          <Segmented<Language>
            label={t("me.language")}
            value={i18n.language === "en" ? "en" : "ro"}
            onChange={changeLanguage}
            options={[
              { value: "ro", label: t("languages.ro") },
              { value: "en", label: t("languages.en") },
            ]}
          />
          <Segmented<Theme>
            label={t("me.theme")}
            value={theme}
            onChange={(value) => {
              setTheme(value);
              setThemeState(value);
            }}
            options={[
              { value: "system", label: t("themes.system") },
              { value: "light", label: t("themes.light") },
              { value: "dark", label: t("themes.dark") },
            ]}
          />
        </Stack>
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
