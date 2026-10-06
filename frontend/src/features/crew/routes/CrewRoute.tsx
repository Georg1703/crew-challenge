import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";

import { useMe } from "@/features/auth";
import { ProposalsRow } from "@/features/challenges";
import { CrewFeed, useFeed, useToday } from "@/features/checkins";
import { errorMessage } from "@/i18n/errors";
import { Banner, Button, Icon, Screen, Skeleton } from "@/shared/ui";

import { useCrew } from "../api";
import { CrewStories } from "../components/CrewStories";
import { freshCounts, markSeen, useSeenVersion } from "../seen";

const DAY_MS = 24 * 60 * 60 * 1000;

/**
 * Echipa, the crew's journal: everyone's day as a row of rings (each opens their page), the
 * proposals when there are some, then day by day what the crew did. Members and invites are one
 * tap away, behind the button next to the title.
 */
export function CrewRoute() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const me = useMe();
  const crew = useCrew();
  const today = useToday();
  const feed = useFeed();
  useSeenVersion();
  // Never looked at someone's proofs on this device: the last day's count as new.
  const [since] = useState(() => new Date(Date.now() - DAY_MS));
  const isAdmin = me.data?.member?.role === "admin";
  const meId = me.data?.member?.id;
  const items = feed.data?.pages.flatMap((page) => page.results) ?? [];
  const fresh = crew.data ? freshCounts(items, crew.data.id, meId, since) : {};

  return (
    <Screen
      title={crew.data?.name ?? t("crew.title")}
      action={
        <Button
          variant="ghost"
          aria-label={t("crew.members.open")}
          icon={<Icon name="users" size={22} />}
          onClick={() => navigate("/crew/members")}
        />
      }
    >
      {crew.isPending && <Skeleton lines={4} />}
      {crew.isError && (
        <Banner
          tone="danger"
          title={errorMessage(t, crew.error)}
          actions={
            <Button variant="ghost" onClick={() => void crew.refetch()}>
              {t("common.retry")}
            </Button>
          }
        />
      )}
      {crew.data && (
        <>
          <CrewStories
            members={crew.data.members}
            meId={meId}
            today={today.data?.crew}
            fresh={fresh}
          />
          <ProposalsRow isAdmin={isAdmin} timeZone={crew.data.timezone} />
          <CrewFeed
            timeZone={crew.data.timezone}
            members={crew.data.members}
            onOpenProofOf={(memberId) => crew.data && markSeen(crew.data.id, memberId)}
          />
        </>
      )}
    </Screen>
  );
}
