import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router";

import { isApiError } from "@/api";
import { errorMessage } from "@/i18n/errors";
import { monthName } from "@/shared/lib/format";
import {
  Banner,
  Button,
  ChipGroup,
  IconPicker,
  OptionList,
  Screen,
  Skeleton,
  Stack,
  StepProgress,
  Stepper,
  TextArea,
  TextField,
  Toggle,
  useToast,
} from "@/shared/ui";

import {
  useChallenge,
  useCurrentRound,
  useEditChallenge,
  useProposeChallenge,
  type ChallengeInput,
} from "../api";
import styles from "../challenges.module.css";
import {
  CHALLENGE_ICONS,
  WEEKDAYS,
  describeFrequency,
  describeMeasure,
  describeProof,
  describeTarget,
  weekdayShort,
} from "../describe";

type Draft = Required<Omit<ChallengeInput, "target_value" | "times">> & {
  times: number;
  target_value: string;
};

const EMPTY: Draft = {
  title: "",
  rules: "",
  icon: "star",
  measure: "check",
  unit: "",
  frequency: "daily",
  weekdays: [0, 1, 2, 3, 4],
  times: 3,
  target_scope: "none",
  target_value: "",
  proof_kind: "none",
  proof_required: false,
};

const STEPS = ["what", "often", "record", "proof", "review"] as const;
type Step = (typeof STEPS)[number];

/** Which step shows each field, to send people back to the field the server rejected. */
const FIELD_STEP: Record<string, Step> = {
  title: "what",
  rules: "what",
  icon: "what",
  frequency: "often",
  weekdays: "often",
  times: "often",
  measure: "record",
  unit: "record",
  target_scope: "record",
  target_value: "record",
  proof_kind: "proof",
  proof_required: "proof",
};

function toInput(draft: Draft): ChallengeInput {
  const quantity = draft.measure === "quantity";
  const target = quantity ? draft.target_scope : "none";
  return {
    title: draft.title,
    rules: draft.rules,
    icon: draft.icon,
    measure: draft.measure,
    unit: quantity ? draft.unit : "",
    frequency: draft.frequency,
    weekdays: draft.frequency === "weekdays" ? draft.weekdays : [],
    times: draft.frequency.startsWith("times_") ? draft.times : null,
    target_scope: target,
    target_value: target === "none" ? null : draft.target_value.replace(",", "."),
    proof_kind: draft.proof_kind,
    proof_required: draft.proof_kind !== "none" && draft.proof_required,
  };
}

/** /challenges/new and /challenges/:id/edit */
export function ProposeRoute() {
  const { id } = useParams();
  return id ? <EditProposal id={id} /> : <ProposeWizard initial={EMPTY} />;
}

function EditProposal({ id }: { id: string }) {
  const { t } = useTranslation();
  const challenge = useChallenge(id);
  if (challenge.isPending) {
    return (
      <Screen withTabBar={false}>
        <Skeleton lines={5} />
      </Screen>
    );
  }
  if (!challenge.data) {
    return (
      <Screen withTabBar={false} title={t("challenges.title")}>
        <Banner tone="danger" title={errorMessage(t, challenge.error)} />
      </Screen>
    );
  }
  const c = challenge.data;
  return (
    <ProposeWizard
      editingId={id}
      initial={{
        title: c.title,
        rules: c.rules,
        icon: c.icon,
        measure: c.measure,
        unit: c.unit,
        frequency: c.frequency,
        weekdays: c.weekdays.length ? c.weekdays : EMPTY.weekdays,
        times: c.times ?? EMPTY.times,
        target_scope: c.target_scope,
        target_value: c.target_value == null ? "" : String(c.target_value),
        proof_kind: c.proof_kind,
        proof_required: c.proof_required,
      }}
    />
  );
}

function ProposeWizard({ initial, editingId }: { initial: Draft; editingId?: string }) {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const toast = useToast();
  const round = useCurrentRound();
  const propose = useProposeChallenge();
  const edit = useEditChallenge(editingId ?? "");
  const save = editingId ? edit : propose;
  const [draft, setDraft] = useState<Draft>(initial);
  const [step, setStep] = useState<Step>("what");
  const [localErrors, setLocalErrors] = useState<Record<string, string>>({});

  const index = STEPS.indexOf(step);
  const apiError = isApiError(save.error) ? save.error : undefined;
  const fieldError = (name: string) => localErrors[name] ?? apiError?.field(name);
  const set = <K extends keyof Draft>(key: K, value: Draft[K]) =>
    setDraft((current) => ({ ...current, [key]: value }));
  const month = round.data ? monthName(round.data.period_start, i18n.language) : "";

  /** The checks a person needs before moving on; the server checks everything again. */
  const check = (current: Step): Record<string, string> => {
    const errors: Record<string, string> = {};
    if (current === "what" && !draft.title.trim()) errors.title = t("challenges.errors.title");
    if (current === "often" && draft.frequency === "weekdays" && !draft.weekdays.length)
      errors.weekdays = t("challenges.errors.weekdays");
    if (current === "record" && draft.measure === "quantity") {
      if (!draft.unit.trim()) errors.unit = t("challenges.errors.unit");
      if (draft.target_scope !== "none" && !(Number(draft.target_value.replace(",", ".")) > 0))
        errors.target_value = t("challenges.errors.targetValue");
    }
    return errors;
  };

  const next = (event: FormEvent) => {
    event.preventDefault();
    const errors = check(step);
    setLocalErrors(errors);
    if (Object.keys(errors).length) return;
    if (step !== "review") return setStep(STEPS[index + 1] ?? "review");
    save.mutate(toInput(draft), {
      onSuccess: (challenge) => {
        toast(editingId ? t("challenges.saved") : t("challenges.published"), "success");
        navigate(`/challenges/${challenge.id}`, { replace: true });
      },
      onError: (error) => {
        const field = isApiError(error) ? Object.keys(error.fields ?? {})[0] : undefined;
        if (field && FIELD_STEP[field]) setStep(FIELD_STEP[field]);
      },
    });
  };

  const back = () => (index === 0 ? navigate(-1) : setStep(STEPS[index - 1] ?? "what"));
  const generalError =
    save.error && !Object.keys(apiError?.fields ?? {}).length ? errorMessage(t, save.error) : null;

  return (
    <Screen withTabBar={false} title={t(`challenges.steps.${step}.title`)}>
      <div className={styles.wizardTop}>
        <StepProgress
          current={index + 1}
          total={STEPS.length}
          label={t("challenges.stepLabel", { n: index + 1, total: STEPS.length })}
        />
        <p className={styles.meta}>
          {editingId
            ? t("challenges.editingFor", { month })
            : t("challenges.proposingFor", { month })}
        </p>
      </div>
      {generalError && <Banner tone="danger" title={generalError} />}

      <form onSubmit={next} noValidate>
        <Stack gap="lg">
          {step === "what" && (
            <Stack>
              <TextField
                label={t("challenges.fields.title")}
                hint={t("challenges.fields.titleHint")}
                maxLength={60}
                value={draft.title}
                onChange={(e) => set("title", e.target.value)}
                error={fieldError("title")}
              />
              <IconPicker
                label={t("challenges.fields.icon")}
                value={draft.icon}
                onChange={(icon) => set("icon", icon)}
                options={(Object.keys(CHALLENGE_ICONS) as Draft["icon"][]).map((key) => ({
                  value: key,
                  icon: CHALLENGE_ICONS[key],
                  name: t(`challenges.icons.${key}`),
                }))}
              />
              <TextArea
                label={t("challenges.fields.rules")}
                hint={t("challenges.fields.rulesHint")}
                maxLength={500}
                value={draft.rules}
                onChange={(e) => set("rules", e.target.value)}
                error={fieldError("rules")}
              />
            </Stack>
          )}

          {step === "often" && (
            <Stack>
              <OptionList
                label={t("challenges.fields.frequency")}
                value={draft.frequency}
                onChange={(frequency) => set("frequency", frequency)}
                options={(
                  ["daily", "weekdays", "times_per_week", "times_per_period", "once"] as const
                ).map((value) => ({
                  value,
                  title: t(`challenges.options.frequency.${value}.title`),
                  description: t(`challenges.options.frequency.${value}.description`),
                }))}
              />
              {draft.frequency === "weekdays" && (
                <ChipGroup
                  label={t("challenges.fields.weekdays")}
                  values={draft.weekdays}
                  onChange={(days) => set("weekdays", [...days].sort())}
                  error={fieldError("weekdays")}
                  options={WEEKDAYS.map((day) => ({
                    value: day,
                    label: weekdayShort(t, day),
                    name: t(`challenges.days.long.${day}`),
                  }))}
                />
              )}
              {draft.frequency.startsWith("times_") && (
                <Stepper
                  label={t("challenges.fields.times")}
                  value={draft.times}
                  min={1}
                  max={draft.frequency === "times_per_week" ? 7 : 31}
                  onChange={(times) => set("times", times)}
                  decreaseLabel={t("challenges.fields.fewer")}
                  increaseLabel={t("challenges.fields.more")}
                />
              )}
            </Stack>
          )}

          {step === "record" && (
            <Stack>
              <OptionList
                label={t("challenges.fields.measure")}
                value={draft.measure}
                onChange={(measure) => set("measure", measure)}
                options={(["check", "quantity", "abstain"] as const).map((value) => ({
                  value,
                  title: t(`challenges.options.measure.${value}.title`),
                  description: t(`challenges.options.measure.${value}.description`),
                }))}
              />
              {draft.measure === "quantity" && (
                <>
                  <TextField
                    label={t("challenges.fields.unit")}
                    hint={t("challenges.fields.unitHint")}
                    maxLength={20}
                    value={draft.unit}
                    onChange={(e) => set("unit", e.target.value)}
                    error={fieldError("unit")}
                  />
                  <OptionList
                    label={t("challenges.fields.target")}
                    value={draft.target_scope}
                    onChange={(scope) => set("target_scope", scope)}
                    columns={2}
                    options={(["none", "per_check_in", "per_week", "per_period"] as const).map(
                      (value) => ({ value, title: t(`challenges.options.target.${value}`) }),
                    )}
                  />
                  {draft.target_scope !== "none" && (
                    <TextField
                      label={t("challenges.fields.targetValue", { unit: draft.unit })}
                      inputMode="decimal"
                      value={draft.target_value}
                      onChange={(e) => set("target_value", e.target.value)}
                      error={fieldError("target_value")}
                    />
                  )}
                </>
              )}
            </Stack>
          )}

          {step === "proof" && (
            <Stack>
              <OptionList
                label={t("challenges.fields.proof")}
                value={draft.proof_kind}
                onChange={(kind) => set("proof_kind", kind)}
                options={(["none", "photo", "video", "photo_or_video"] as const).map((value) => ({
                  value,
                  title: t(`challenges.options.proof.${value}.title`),
                  description: t(`challenges.options.proof.${value}.description`),
                }))}
              />
              {draft.proof_kind !== "none" && (
                <Toggle
                  label={t("challenges.fields.proofRequired")}
                  description={t("challenges.fields.proofRequiredHint")}
                  checked={draft.proof_required}
                  onChange={(on) => set("proof_required", on)}
                />
              )}
            </Stack>
          )}

          {step === "review" && <Review draft={draft} editing={Boolean(editingId)} />}

          <div className={styles.wizardNav}>
            <Button variant="secondary" size="lg" onClick={back}>
              {t("challenges.back")}
            </Button>
            <Button type="submit" size="lg" loading={save.isPending}>
              {step === "review"
                ? editingId
                  ? t("challenges.save")
                  : t("challenges.publish")
                : t("challenges.next")}
            </Button>
          </div>
        </Stack>
      </form>
    </Screen>
  );
}

function Review({ draft, editing }: { draft: Draft; editing: boolean }) {
  const { t, i18n } = useTranslation();
  const input = toInput(draft);
  const shape = {
    ...input,
    weekdays: input.weekdays ?? [],
    times: input.times ?? null,
    target_value: input.target_value == null ? null : Number(input.target_value),
  };
  const target = describeTarget(t, shape, i18n.language);
  const facts: [string, string][] = [
    [t("challenges.facts.name"), draft.title.trim()],
    [t("challenges.facts.often"), describeFrequency(t, shape)],
    [t("challenges.facts.record"), describeMeasure(t, shape)],
    ...(target ? [[t("challenges.facts.target"), target] as [string, string]] : []),
    [t("challenges.facts.proof"), describeProof(t, shape)],
  ];
  return (
    <Stack>
      <dl className={styles.facts}>
        {facts.map(([label, value]) => (
          <div key={label} className={styles.factRow}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
      {draft.rules.trim() && <p className={styles.muted}>{draft.rules.trim()}</p>}
      <p className={styles.meta}>
        {editing ? t("challenges.editResetsVotes") : t("challenges.reviewNote")}
      </p>
    </Stack>
  );
}
