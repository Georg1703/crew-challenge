import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Navigate, useNavigate, useSearchParams } from "react-router";

import { errorMessage } from "@/i18n/errors";
import { Banner, Button, Screen, Stack, TextField } from "@/shared/ui";

import { useLogin, useMe } from "../api";
import styles from "../auth.module.css";
import { safeNext } from "../next";

/** 1.7 Log in (and 1.8 when the password is wrong). */
export function LoginRoute() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const next = safeNext(params.get("next"));
  const joining = next.startsWith("/join/");
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
    <Screen withTabBar={false} title={t("auth.loginTitle")}>
      {login.error && <Banner tone="danger" title={errorMessage(t, login.error)} />}
      {joining && <p className={styles.muted}>{t("auth.joiningAs")}</p>}
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
            required
          />
          <Button type="submit" size="lg" fullWidth loading={login.isPending}>
            {t("auth.login")}
          </Button>
        </Stack>
      </form>
      <p className={styles.note}>{t("auth.noAccount")}</p>
    </Screen>
  );
}
