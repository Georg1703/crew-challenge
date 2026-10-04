import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { errorMessage } from "@/i18n/errors";
import { formatDate } from "@/shared/lib/format";
import { AvatarStack, Button, Card, Icon, useToast } from "@/shared/ui";

import { useVote, type Proposal, type Round } from "../api";
import styles from "../challenges.module.css";
import { summaryLine } from "../describe";
import { ChallengeIcon } from "./ChallengeIcon";
import { ChooseSheet } from "./ChooseSheet";

/** The open round's proposals: who proposed, the votes, your vote, and the admin's choice. */
export function RoundProposals({
  round,
  isAdmin,
  timeZone,
}: {
  round: Round;
  isAdmin: boolean;
  timeZone: string;
}) {
  const { t, i18n } = useTranslation();
  const toast = useToast();
  const vote = useVote();
  const [choosing, setChoosing] = useState<Proposal | null>(null);

  const toggleVote = (proposal: Proposal) =>
    vote.mutate(
      {
        roundId: round.id,
        challengeId: round.my_vote === proposal.id ? null : proposal.id,
      },
      { onError: (error) => toast(errorMessage(t, error), "error") },
    );

  return (
    <div className={styles.proposals}>
      {round.proposals.map((proposal) => {
        const mine = round.my_vote === proposal.id;
        return (
          <Card key={proposal.id}>
            <Link to={`/challenges/${proposal.id}`} className={styles.cardLink}>
              <ChallengeIcon icon={proposal.icon} />
              <span className={styles.cardText}>
                <span className={styles.cardTitle}>{proposal.title}</span>
                <span className={styles.meta}>{summaryLine(t, proposal, i18n.language)}</span>
                <span className={styles.meta}>
                  {t("challenges.proposedBy", {
                    name: proposal.created_by?.display_name ?? t("challenges.someone"),
                    date: formatDate(proposal.created_at, i18n.language, timeZone),
                  })}
                </span>
              </span>
              <Icon name="chevronRight" size={20} />
            </Link>
            <div className={styles.voteRow}>
              <span className={styles.votes}>
                {proposal.voters.length > 0 && (
                  <AvatarStack
                    label={proposal.voters.map((voter) => voter.display_name).join(", ")}
                    members={proposal.voters.map((voter) => ({
                      id: voter.id,
                      name: voter.display_name,
                      seed: voter.avatar_seed,
                    }))}
                  />
                )}
                {t("challenges.votes", { n: proposal.vote_count })}
              </span>
              <span className={styles.voteActions}>
                {isAdmin && (
                  <Button variant="ghost" onClick={() => setChoosing(proposal)}>
                    {t("challenges.choose")}
                  </Button>
                )}
                <Button
                  variant={mine ? "primary" : "secondary"}
                  icon={mine ? <Icon name="check" size={20} /> : undefined}
                  aria-pressed={mine}
                  onClick={() => toggleVote(proposal)}
                >
                  {mine ? t("challenges.voted") : t("challenges.vote")}
                </Button>
              </span>
            </div>
          </Card>
        );
      })}
      <ChooseSheet round={round} proposal={choosing} onClose={() => setChoosing(null)} />
    </div>
  );
}
