import { useEffect, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router";

import { isApiError, type InvitePreview, type Me } from "@/api";
import { setLanguage } from "@/i18n";
import { errorMessage } from "@/i18n/errors";
import { formatDate, formatList } from "@/shared/lib/format";
import { AvatarStack, Banner, Button, Card, Screen, Skeleton, Stack, TextField } from "@/shared/ui";

import { useAcceptInvite, useInvitePreview, useJoinWithAccount, useMe } from "../api";
import styles from "../auth.module.css";

/**
 * /join/:code - the invite link.
 * 1.2 the invite, 1.3 create an account, 1.9 the invite no longer works, and joining with an
 * account you already have when you are logged in.
 */
export function JoinRoute() {
  const { t } = useTranslation();
  const { code = "" } = useParams();
  const preview = useInvitePreview(code);
  const me = useMe();

  if (preview.isPending || me.isPending) {
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
    return <Unavailable message={unavailable ?? t("common.somethingWrong")} signedIn={!!me.data} />;
  }
  if (me.data) return <JoinWithAccount code={code} preview={preview.data} me={me.data} />;
  return <JoinAsNewPerson code={code} preview={preview.data} />;
}

function Unavailable({ message, signedIn }: { message: string; signedIn: boolean }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  return (
    <Screen withTabBar={false} title={t("join.unavailableTitle")}>
      <p className={styles.muted}>{message}</p>
      <Button
        variant="secondary"
        size="lg"
        fullWidth
        onClick={() => navigate(signedIn ? "/" : "/login")}
      >
        {signedIn ? t("join.goHome") : t("join.haveAccount")}
      </Button>
    </Screen>
  );
}

/** Who invited you and who is already in the crew. */
function InviteSummary({ preview }: { preview: InvitePreview }) {
  const { t, i18n } = useTranslation();
  const names = preview.members.map((member) => member.display_name);
  return (
    <Card>
      {preview.invited_by && (
        <p>{t("join.invitedBy", { name: preview.invited_by.display_name })}</p>
      )}
      {names.length > 0 && (
        <div className={styles.members}>
          <AvatarStack
            label={t("join.members", { names: formatList(names, i18n.language) })}
            members={preview.members.map((member, index) => ({
              id: String(index),
              name: member.display_name,
              seed: member.avatar_seed,
            }))}
          />
          <span className={styles.membersText}>{formatList(names, i18n.language)}</span>
        </div>
      )}
    </Card>
  );
}

function JoinAsNewPerson({ code, preview }: { code: string; preview: InvitePreview }) {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const [step, setStep] = useState<"invite" | "account">("invite");

  if (step === "account") {
    return <CreateAccount code={code} onBack={() => setStep("invite")} />;
  }

  return (
    <Screen withTabBar={false} title={t("join.title", { crew: preview.crew_name })}>
      <InviteSummary preview={preview} />
      <div className={styles.actions}>
        <Button size="lg" fullWidth onClick={() => setStep("account")}>
          {t("join.accept")}
        </Button>
        <Button
          variant="secondary"
          size="lg"
          fullWidth
          onClick={() => navigate(`/login?next=${encodeURIComponent(`/join/${code}`)}`)}
        >
          {t("join.haveAccount")}
        </Button>
      </div>
      <p className={styles.note}>
        {t("join.validUntil", { date: formatDate(preview.expires_at, i18n.language) })}
      </p>
    </Screen>
  );
}

function CreateAccount({ code, onBack }: { code: string; onBack: () => void }) {
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
    accept.mutate(form, { onSuccess: () => navigate("/welcome", { replace: true }) });
  };

  const generalError =
    accept.error && !Object.keys(error?.fields ?? {}).length
      ? errorMessage(t, accept.error)
      : undefined;

  return (
    <Screen withTabBar={false} title={t("join.formTitle")}>
      <p className={styles.muted}>{t("join.formBody")}</p>
      {generalError && <Banner tone="danger" title={generalError} />}
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
          <div className={styles.actions}>
            <Button type="submit" size="lg" fullWidth loading={accept.isPending}>
              {t("join.submit")}
            </Button>
            <Button variant="secondary" size="lg" fullWidth onClick={onBack}>
              {t("join.back")}
            </Button>
          </div>
        </Stack>
      </form>
    </Screen>
  );
}

function JoinWithAccount({ code, preview, me }: { code: string; preview: InvitePreview; me: Me }) {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const join = useJoinWithAccount(code);
  const preferred = me.user.preferred_language;

  // A logged-in person sees their own language, as on every other screen after login.
  useEffect(() => {
    if (preferred !== i18n.language) setLanguage(preferred);
  }, [preferred, i18n]);

  const [displayName, setDisplayName] = useState(me.member?.display_name ?? "");
  const error = isApiError(join.error) ? join.error : undefined;
  const generalError =
    join.error && !error?.field("display_name") ? errorMessage(t, join.error) : undefined;

  const submit = (event: FormEvent) => {
    event.preventDefault();
    join.mutate(
      { display_name: displayName },
      { onSuccess: () => navigate("/welcome", { replace: true }) },
    );
  };

  return (
    <Screen withTabBar={false} title={t("join.accountTitle", { crew: preview.crew_name })}>
      <InviteSummary preview={preview} />
      <p className={styles.muted}>{t("join.accountBody", { username: me.user.username })}</p>
      {generalError && <Banner tone="danger" title={generalError} />}
      <form onSubmit={submit} noValidate>
        <Stack>
          <TextField
            label={t("join.displayName")}
            hint={t("join.displayNameHint")}
            name="display_name"
            autoComplete="nickname"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            error={error?.field("display_name")}
            required
          />
          <Button type="submit" size="lg" fullWidth loading={join.isPending}>
            {t("join.accountSubmit")}
          </Button>
        </Stack>
      </form>
    </Screen>
  );
}
