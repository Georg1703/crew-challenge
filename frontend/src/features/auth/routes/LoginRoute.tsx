import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Navigate, useNavigate, useSearchParams } from "react-router";

import { errorMessage } from "@/i18n/errors";
import { Button, Card, Screen, Stack, TextField } from "@/shared/ui";

import { useLogin, useMe } from "../api";
import styles from "../auth.module.css";

export function LoginRoute() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const next = params.get("next") ?? "/";
  const me = useMe();
  const login = useLogin();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  if (me.data) return <Navigate to={next} replace />;

  const submit = (event: FormEvent) => {
    event.preventDefault();
    login.mutate({ username, password }, { onSuccess: () => navigate(next, { replace: true }) });
  };

  return (
    <Screen withTabBar={false}>
      <div className={styles.intro}>
        <p className={styles.brand}>{t("common.appName")}</p>
        <h1 className={styles.title}>{t("auth.loginTitle")}</h1>
        <p className={styles.subtitle}>{t("auth.loginSubtitle")}</p>
      </div>
      <Card>
        <form onSubmit={submit} noValidate>
          <Stack>
            <TextField
              label={t("auth.username")}
              name="username"
              autoComplete="username"
              autoCapitalize="none"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
            <TextField
              label={t("auth.password")}
              name="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              error={login.error ? errorMessage(t, login.error) : undefined}
              required
            />
            <Button type="submit" size="lg" fullWidth loading={login.isPending}>
              {t("auth.login")}
            </Button>
          </Stack>
        </form>
      </Card>
    </Screen>
  );
}
