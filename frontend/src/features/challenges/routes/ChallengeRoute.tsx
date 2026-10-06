import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router";

import { useMe } from "@/features/auth";
import { ChallengeBoard, CheckInSheet, useToday } from "@/features/checkins";
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
  useLeave,
  useUnschedule,
  useVote,
  useWithdrawChallenge,
  type Challenge,
} from "../api";
import styles from "../challenges.module.css";
import { describeFrequency, describeMeasure, describeProof, describeTarget } from "../describe";
import { ChallengeIcon } from "../components/ChallengeIcon";
import { PhasePill } from "../components/PhasePill";
import { ParticipantsSheet } from "../components/ParticipantsSheet";
import { ScheduleSheet } from "../components/ScheduleSheet";

/** One challenge: what it asks, how the crew is doing, who takes part and who proposed it. */
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

function ChallengeScreen({ challenge }: { challenge: Challenge }) {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const toast = useToast();
  const me = useMe();
  const member = me.data?.member;
  const timeZone = me.data?.crew?.timezone ?? "UTC";
  const leave = useLeave(challenge.id);
  const withdraw = useWithdrawChallenge();
  const unschedule = useUnschedule(challenge.id);
  const vote = useVote();
  const [withdrawing, setWithdrawing] = useState(false);
  const [leaving, setLeaving] = useState(false);
  const [scheduling, setScheduling] = useState(false);
  const [inviting, setInviting] = useState(false);
  const [checkingIn, setCheckingIn] = useState(false);
  const today = useToday({ enabled: challenge.phase === "active" && challenge.taking_part });

  const mine = challenge.mine;
  const isAdmin = member?.role === "admin";
  const proposal = challenge.state === "proposed";
  const notStarted = challenge.phase === "upcoming";
  const target = describeTarget(t, challenge, i18n.language);

  const facts = [
    describeFrequency(t, challenge),
    describeMeasure(t, challenge),
    describeProof(t, challenge),
  ];
  const period =
    challenge.period_start && challenge.start_date
      ? challenge.start_date === challenge.period_start
        ? monthAndYear(challenge.period_start, i18n.language)
        : t("challenges.periodFrom", {
            month: monthAndYear(challenge.period_start, i18n.language),
            date: formatDay(challenge.start_date, i18n.language),
          })
      : null;
  const footnotes = [
    period && t("challenges.periodLine", { period }),
    t("challenges.proposedBy", {
      name: challenge.created_by?.display_name ?? t("challenges.someone"),
      date: formatDate(challenge.created_at, i18n.language, timeZone),
    }),
    challenge.chosen_by &&
      challenge.chosen_at &&
      t("challenges.chosenBy", {
        name: challenge.chosen_by.display_name,
        date: formatDate(challenge.chosen_at, i18n.language, timeZone),
      }),
    proposal && t("challenges.votes", { n: challenge.vote_count }),
  ].filter((line): line is string => Boolean(line));
  const running = challenge.state === "chosen" && challenge.phase !== "upcoming";
  const myToday = today.data?.challenges.find((c) => c.id === challenge.id);
  const canCheckIn =
    challenge.phase === "active" &&
    myToday !== undefined &&
    (myToday.settled === false || myToday.state === "partial");

  const started = challenge.phase === "active";
  const leaveNow = () =>
    leave.mutate(undefined, {
      onSuccess: () => {
        toast(started ? t("challenges.left") : t("challenges.optedOut"), "success");
        navigate("/challenges", { replace: true });
      },
    });

  return (
    <Screen title={challenge.title}>
      <div className={styles.header}>
        <ChallengeIcon icon={challenge.icon} />
        <ul className={styles.factPills} aria-label={t("challenges.factsLabel")}>
          {challenge.phase !== "active" && (
            <li>
              <PhasePill challenge={challenge} />
            </li>
          )}
          {facts.map((fact) => (
            <li key={fact}>
              <StatusPill>{fact}</StatusPill>
            </li>
          ))}
        </ul>
      </div>
      {target && <p className={styles.muted}>{target}</p>}
      {challenge.rules && <p>{challenge.rules}</p>}

      {proposal && (
        <div className={styles.actions}>
          {challenge.taking_part && (
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
            {challenge.participants.map(({ member: person }) => (
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
          {!challenge.taking_part && <p className={styles.meta}>{t("challenges.who.adminOnly")}</p>}
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

      {running && challenge.start_date && challenge.end_date && (
        <ChallengeBoard
          challengeId={challenge.id}
          title={challenge.title}
          unit={challenge.unit}
          startDate={challenge.start_date}
          endDate={challenge.end_date}
          timeZone={timeZone}
          meId={member?.id}
          fixedDays={challenge.frequency === "daily" || challenge.frequency === "weekdays"}
          leftOn={Object.fromEntries(
            challenge.participants.flatMap((p) => (p.left_on ? [[p.member.id, p.left_on]] : [])),
          )}
        />
      )}

      {canCheckIn && (
        <Button
          size="lg"
          fullWidth
          icon={<Icon name="check" size={20} />}
          onClick={() => setCheckingIn(true)}
        >
          {t("challenges.checkIn")}
        </Button>
      )}

      <ul className={styles.footnotes}>
        {footnotes.map((line) => (
          <li key={line}>{line}</li>
        ))}
      </ul>

      {challenge.state === "chosen" && (
        <section className={styles.section}>
          {!running && (
            <>
              <h2 className={styles.sectionTitle}>{t("challenges.participantsTitle")}</h2>
              <ParticipantList challenge={challenge} meId={member?.id} />
            </>
          )}
          {challenge.phase !== "finished" && challenge.taking_part && (
            <Button variant="danger" size="lg" fullWidth onClick={() => setLeaving(true)}>
              {started ? t("challenges.leave") : t("challenges.optOut")}
            </Button>
          )}
        </section>
      )}

      {checkingIn && (
        <CheckInSheet challengeId={challenge.id} onClose={() => setCheckingIn(false)} />
      )}

      {inviting && <ParticipantsSheet challenge={challenge} onClose={() => setInviting(false)} />}

      <Sheet
        open={leaving}
        onClose={() => setLeaving(false)}
        title={started ? t("challenges.leaveTitle") : t("challenges.optOutTitle")}
        closeLabel={t("common.close")}
      >
        <p className={styles.muted}>
          {started ? t("challenges.leaveBody") : t("challenges.optOutBody")}
        </p>
        {leave.error && <Banner tone="danger" title={errorMessage(t, leave.error)} />}
        <div className={styles.actions}>
          <Button variant="danger" size="lg" fullWidth loading={leave.isPending} onClick={leaveNow}>
            {started ? t("challenges.leave") : t("challenges.optOut")}
          </Button>
          <Button variant="secondary" size="lg" fullWidth onClick={() => setLeaving(false)}>
            {t("common.cancel")}
          </Button>
        </div>
      </Sheet>

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

/** Who takes part in a scheduled challenge that has not started (the board shows them after). */
function ParticipantList({ challenge, meId }: { challenge: Challenge; meId?: string }) {
  const { t, i18n } = useTranslation();
  return (
    <List label={t("challenges.participantsTitle")}>
      {challenge.participants.map((p) => (
        <ListRow
          key={p.member.id}
          leading={<Avatar name={p.member.display_name} seed={p.member.avatar_seed} />}
          title={p.member.display_name}
          subtitle={
            p.left_on
              ? t("challenges.leftOn", { date: formatDay(p.left_on, i18n.language) })
              : undefined
          }
          trailing={
            p.member.id === meId ? (
              <StatusPill tone="accent">{t("crew.you")}</StatusPill>
            ) : undefined
          }
        />
      ))}
    </List>
  );
}
