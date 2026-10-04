import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router";

import { useMe } from "@/features/auth";
import { errorMessage } from "@/i18n/errors";
import { formatDate, formatDay } from "@/shared/lib/format";
import {
  Avatar,
  Banner,
  Button,
  Icon,
  List,
  ListRow,
  Screen,
  Sheet,
  Skeleton,
  StatusPill,
  useToast,
} from "@/shared/ui";

import {
  useChallenge,
  useParticipation,
  useRepropose,
  useWithdrawChallenge,
  type ChallengeDetail,
} from "../api";
import styles from "../challenges.module.css";
import { describeFrequency, describeMeasure, describeProof, describeTarget } from "../describe";
import { ChallengeIcon } from "../components/ChallengeIcon";
import { PhasePill } from "../components/PhasePill";

/** One challenge: its rules in plain words, who proposed it, and who takes part. */
export function ChallengeRoute() {
  const { t } = useTranslation();
  const { id = "" } = useParams();
  const challenge = useChallenge(id);

  if (challenge.isPending) {
    return (
      <Screen title={t("challenges.title")}>
        <Skeleton lines={5} />
      </Screen>
    );
  }
  if (challenge.error || !challenge.data) {
    return (
      <Screen title={t("challenges.title")}>
        <Banner tone="danger" title={errorMessage(t, challenge.error)} />
      </Screen>
    );
  }
  return <ChallengeScreen challenge={challenge.data} />;
}

function ChallengeScreen({ challenge }: { challenge: ChallengeDetail }) {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const toast = useToast();
  const me = useMe();
  const member = me.data?.member;
  const timeZone = me.data?.crew?.timezone ?? "UTC";
  const participation = useParticipation(challenge.id);
  const withdraw = useWithdrawChallenge();
  const repropose = useRepropose();
  const [withdrawing, setWithdrawing] = useState(false);

  const mine = challenge.created_by?.id === member?.id;
  const proposal = challenge.state === "proposed";
  const target = describeTarget(t, challenge, i18n.language);

  const facts: [string, string][] = [
    [t("challenges.facts.often"), describeFrequency(t, challenge)],
    [t("challenges.facts.record"), describeMeasure(t, challenge)],
    ...(target ? [[t("challenges.facts.target"), target] as [string, string]] : []),
    [t("challenges.facts.proof"), describeProof(t, challenge)],
    ...(challenge.start_date && challenge.end_date
      ? [
          [
            t("challenges.facts.period"),
            t("challenges.dates", {
              start: formatDay(challenge.start_date, i18n.language),
              end: formatDay(challenge.end_date, i18n.language),
            }),
          ] as [string, string],
        ]
      : []),
    [
      t("challenges.facts.proposed"),
      t("challenges.proposedBy", {
        name: challenge.created_by?.display_name ?? t("challenges.someone"),
        date: formatDate(challenge.created_at, i18n.language, timeZone),
      }),
    ],
  ];

  const toggleParticipation = () =>
    participation.mutate(!challenge.taking_part, {
      onError: (error) => toast(errorMessage(t, error), "error"),
    });

  return (
    <Screen title={challenge.title}>
      <div className={styles.header}>
        <ChallengeIcon icon={challenge.icon} />
        <PhasePill challenge={challenge} />
      </div>
      {challenge.rules && <p>{challenge.rules}</p>}
      <dl className={styles.facts}>
        {facts.map(([label, value]) => (
          <div key={label} className={styles.factRow}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>

      {proposal && mine && (
        <div className={styles.actions}>
          <Button
            variant="secondary"
            size="lg"
            fullWidth
            icon={<Icon name="pencil" size={20} />}
            onClick={() => navigate(`/challenges/${challenge.id}/edit`)}
          >
            {t("challenges.edit")}
          </Button>
        </div>
      )}
      {proposal && (mine || member?.role === "admin") && (
        <Button
          variant="danger"
          fullWidth
          icon={<Icon name="trash" size={20} />}
          onClick={() => setWithdrawing(true)}
        >
          {t("challenges.withdraw")}
        </Button>
      )}

      {challenge.state === "not_chosen" && (
        <Button
          variant="secondary"
          size="lg"
          fullWidth
          loading={repropose.isPending}
          onClick={() =>
            repropose.mutate(challenge.id, {
              onSuccess: (copy) => {
                toast(t("challenges.reproposed"), "success");
                navigate(`/challenges/${copy.id}`, { replace: true });
              },
              onError: (error) => toast(errorMessage(t, error), "error"),
            })
          }
        >
          {t("challenges.repropose")}
        </Button>
      )}

      {challenge.state === "chosen" && (
        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>{t("challenges.participantsTitle")}</h2>
          <List label={t("challenges.participantsTitle")}>
            {challenge.participants.map((p) => (
              <ListRow
                key={p.member.id}
                leading={<Avatar name={p.member.display_name} seed={p.member.avatar_seed} />}
                title={p.member.display_name}
                subtitle={
                  p.ended_on
                    ? t("challenges.leftOn", { date: formatDay(p.ended_on, i18n.language) })
                    : undefined
                }
                trailing={
                  p.member.id === member?.id ? (
                    <StatusPill tone="accent">{t("crew.you")}</StatusPill>
                  ) : undefined
                }
              />
            ))}
          </List>
          {challenge.phase !== "finished" && (
            <Button
              variant={challenge.taking_part ? "danger" : "primary"}
              size="lg"
              fullWidth
              loading={participation.isPending}
              disabled={!challenge.taking_part && challenge.phase === "active"}
              onClick={toggleParticipation}
            >
              {challenge.taking_part
                ? challenge.phase === "active"
                  ? t("challenges.leave")
                  : t("challenges.optOut")
                : t("challenges.optIn")}
            </Button>
          )}
        </section>
      )}

      <Sheet
        open={withdrawing}
        onClose={() => setWithdrawing(false)}
        title={t("challenges.withdrawTitle")}
        closeLabel={t("common.close")}
      >
        <p className={styles.muted}>{t("challenges.withdrawBody")}</p>
        {withdraw.error && <Banner tone="danger" title={errorMessage(t, withdraw.error)} />}
        <div className={styles.actions}>
          <Button
            variant="danger"
            size="lg"
            fullWidth
            loading={withdraw.isPending}
            onClick={() =>
              withdraw.mutate(challenge.id, {
                onSuccess: () => {
                  toast(t("challenges.withdrawn"), "success");
                  navigate("/challenges", { replace: true });
                },
              })
            }
          >
            {t("challenges.withdrawConfirm")}
          </Button>
          <Button variant="secondary" size="lg" fullWidth onClick={() => setWithdrawing(false)}>
            {t("common.cancel")}
          </Button>
        </div>
      </Sheet>
    </Screen>
  );
}
