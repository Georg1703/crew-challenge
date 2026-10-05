import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router";

import { useMe } from "@/features/auth";
import { ChallengeBoard } from "@/features/checkins";
import { errorMessage } from "@/i18n/errors";
import { formatDate, formatDay, monthAndYear } from "@/shared/lib/format";
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
  useUnschedule,
  useVote,
  useWithdrawChallenge,
  type ChallengeDetail,
} from "../api";
import styles from "../challenges.module.css";
import { describeFrequency, describeMeasure, describeProof, describeTarget } from "../describe";
import { ChallengeIcon } from "../components/ChallengeIcon";
import { PhasePill } from "../components/PhasePill";
import { InviteesSheet } from "../components/InviteesSheet";
import { ScheduleSheet } from "../components/ScheduleSheet";

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
  const unschedule = useUnschedule(challenge.id);
  const vote = useVote();
  const [withdrawing, setWithdrawing] = useState(false);
  const [scheduling, setScheduling] = useState(false);
  const [inviting, setInviting] = useState(false);

  const mine = challenge.mine;
  const isAdmin = member?.role === "admin";
  const proposal = challenge.state === "proposed";
  const notStarted = challenge.phase === "upcoming";
  const target = describeTarget(t, challenge, i18n.language);

  const facts: [string, string][] = [
    [t("challenges.facts.often"), describeFrequency(t, challenge)],
    [t("challenges.facts.record"), describeMeasure(t, challenge)],
    ...(target ? [[t("challenges.facts.target"), target] as [string, string]] : []),
    [t("challenges.facts.proof"), describeProof(t, challenge)],
    ...(challenge.period_start && challenge.start_date
      ? [
          [
            t("challenges.facts.period"),
            challenge.start_date === challenge.period_start
              ? monthAndYear(challenge.period_start, i18n.language)
              : t("challenges.periodFrom", {
                  month: monthAndYear(challenge.period_start, i18n.language),
                  date: formatDay(challenge.start_date, i18n.language),
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
    ...(challenge.chosen_by && challenge.chosen_at
      ? [
          [
            t("challenges.facts.chosen"),
            t("challenges.chosenBy", {
              name: challenge.chosen_by.display_name,
              date: formatDate(challenge.chosen_at, i18n.language, timeZone),
            }),
          ] as [string, string],
        ]
      : []),
    [t("challenges.facts.votes"), t("challenges.votes", { n: challenge.vote_count })],
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

      {proposal && (
        <div className={styles.actions}>
          {challenge.invited && (
            <Button
              variant={challenge.my_vote ? "primary" : "secondary"}
              size="lg"
              fullWidth
              icon={challenge.my_vote ? <Icon name="check" size={20} /> : undefined}
              aria-pressed={challenge.my_vote}
              loading={vote.isPending}
              onClick={() =>
                vote.mutate(
                  { id: challenge.id, vote: !challenge.my_vote },
                  { onError: (error) => toast(errorMessage(t, error), "error") },
                )
              }
            >
              {challenge.my_vote ? t("challenges.voted") : t("challenges.vote")}
            </Button>
          )}
          {isAdmin && (
            <Button
              size="lg"
              fullWidth
              icon={<Icon name="flag" size={20} />}
              onClick={() => setScheduling(true)}
            >
              {t("challenges.schedule.open")}
            </Button>
          )}
          {mine && (
            <Button
              variant="secondary"
              size="lg"
              fullWidth
              icon={<Icon name="pencil" size={20} />}
              onClick={() => navigate(`/challenges/${challenge.id}/edit`)}
            >
              {t("challenges.edit")}
            </Button>
          )}
          {(mine || isAdmin) && (
            <Button
              variant="danger"
              fullWidth
              icon={<Icon name="trash" size={20} />}
              onClick={() => setWithdrawing(true)}
            >
              {t("challenges.withdraw")}
            </Button>
          )}
        </div>
      )}

      {isAdmin && challenge.state === "chosen" && notStarted && (
        <div className={styles.actions}>
          <Button variant="secondary" size="lg" fullWidth onClick={() => setScheduling(true)}>
            {t("challenges.schedule.move")}
          </Button>
          <Button
            variant="secondary"
            size="lg"
            fullWidth
            loading={unschedule.isPending}
            onClick={() =>
              unschedule.mutate(undefined, {
                onSuccess: () => toast(t("challenges.schedule.backDone"), "success"),
                onError: (error) => toast(errorMessage(t, error), "error"),
              })
            }
          >
            {t("challenges.schedule.back")}
          </Button>
        </div>
      )}

      {proposal && (
        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>{t("challenges.who.title")}</h2>
          <List label={t("challenges.who.title")}>
            {challenge.invitees.map((person) => (
              <ListRow
                key={person.id}
                leading={<Avatar name={person.display_name} seed={person.avatar_seed} />}
                title={person.display_name}
                trailing={
                  person.id === member?.id ? (
                    <StatusPill tone="accent">{t("crew.you")}</StatusPill>
                  ) : undefined
                }
              />
            ))}
          </List>
          {!challenge.invited && <p className={styles.meta}>{t("challenges.who.adminOnly")}</p>}
          {mine && (
            <Button
              variant="secondary"
              size="lg"
              fullWidth
              icon={<Icon name="users" size={20} />}
              onClick={() => setInviting(true)}
            >
              {t("challenges.who.edit")}
            </Button>
          )}
        </section>
      )}

      {challenge.state === "chosen" &&
        challenge.phase !== "upcoming" &&
        challenge.start_date &&
        challenge.end_date && (
          <ChallengeBoard
            challengeId={challenge.id}
            startDate={challenge.start_date}
            endDate={challenge.end_date}
            timeZone={timeZone}
            meId={member?.id}
            fixedDays={challenge.frequency === "daily" || challenge.frequency === "weekdays"}
            leftOn={Object.fromEntries(
              challenge.participants.flatMap((p) =>
                p.ended_on ? [[p.member.id, p.ended_on]] : [],
              ),
            )}
          />
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
          {challenge.phase !== "finished" && challenge.invited && (
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

      {inviting && <InviteesSheet challenge={challenge} onClose={() => setInviting(false)} />}

      {scheduling && (
        <ScheduleSheet
          challenge={challenge}
          timeZone={timeZone}
          open
          onClose={() => setScheduling(false)}
        />
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
