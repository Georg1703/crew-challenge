import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router";

import { isApiError } from "@/api";
import { errorMessage } from "@/i18n/errors";
import { Button, Card, Screen, Skeleton, Stack, TextField } from "@/shared/ui";

import { useAcceptInvite, useInvitePreview } from "../api";
import styles from "../auth.module.css";

export function JoinRoute() {
  const { t } = useTranslation();
  const { code = "" } = useParams();
  const preview = useInvitePreview(code);

  if (preview.isPending) {
    return (
      <Screen withTabBar={false}>
        <Skeleton lines={4} />
      </Screen>
    );
  }

  const unavailable = preview.isError
    ? isApiError(preview.error) && preview.error.status === 404
      ? t("join.notFound")
      : errorMessage(t, preview.error)
    : preview.data.status === "expired"
      ? t("join.expired")
      : preview.data.status === "used"
        ? t("join.used")
        : null;

  if (unavailable || !preview.data) {
    return (
      <Screen withTabBar={false}>
        <Card>
          <h1 className={styles.cardTitle}>{t("join.unavailableTitle")}</h1>
          <p className={styles.subtitle}>{unavailable}</p>
          <Link className={styles.link} to="/login">
            {t("join.haveAccount")}
          </Link>
        </Card>
      </Screen>
    );
  }

  return <JoinForm code={code} crewName={preview.data.crew_name} />;
}

function JoinForm({ code, crewName }: { code: string; crewName: string }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const accept = useAcceptInvite(code);
  const [form, setForm] = useState({ display_name: "", username: "", password: "" });
  const error = isApiError(accept.error) ? accept.error : undefined;
  const fieldError = (name: string) => error?.field(name);
  const set = (name: keyof typeof form) => (e: { target: { value: string } }) =>
    setForm((current) => ({ ...current, [name]: e.target.value }));

  const submit = (event: FormEvent) => {
    event.preventDefault();
    accept.mutate(form, { onSuccess: () => navigate("/", { replace: true }) });
  };

  const generalError =
    accept.error && !Object.keys(error?.fields ?? {}).length
      ? errorMessage(t, accept.error)
      : undefined;

  return (
    <Screen withTabBar={false}>
      <div className={styles.intro}>
        <p className={styles.brand}>{t("common.appName")}</p>
        <h1 className={styles.title}>{t("join.title", { crew: crewName })}</h1>
        <p className={styles.subtitle}>{t("join.subtitle")}</p>
      </div>
      <Card>
        <form onSubmit={submit} noValidate>
          <Stack>
            <TextField
              label={t("join.displayName")}
              hint={t("join.displayNameHint")}
              name="display_name"
              autoComplete="nickname"
              value={form.display_name}
              onChange={set("display_name")}
              error={fieldError("display_name")}
              required
            />
            <TextField
              label={t("join.username")}
              hint={t("join.usernameHint")}
              name="username"
              autoComplete="username"
              autoCapitalize="none"
              value={form.username}
              onChange={set("username")}
              error={fieldError("username")}
              required
            />
            <TextField
              label={t("join.password")}
              hint={t("join.passwordHint")}
              name="password"
              type="password"
              autoComplete="new-password"
              value={form.password}
              onChange={set("password")}
              error={fieldError("password")}
              required
            />
            {generalError && (
              <p className={styles.error} role="alert">
                {generalError}
              </p>
            )}
            <Button type="submit" size="lg" fullWidth loading={accept.isPending}>
              {t("join.submit")}
            </Button>
          </Stack>
        </form>
      </Card>
    </Screen>
  );
}
