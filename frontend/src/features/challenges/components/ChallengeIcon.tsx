import { Icon, IconTile } from "@/shared/ui";

import type { ChallengeInput } from "../api";
import { CHALLENGE_ICONS } from "../describe";

/** The icon the creator picked, in a tile. */
export function ChallengeIcon({
  icon,
  tone = "accent",
}: {
  icon: ChallengeInput["icon"];
  tone?: "accent" | "neutral";
}) {
  return (
    <IconTile tone={tone}>
      <Icon name={CHALLENGE_ICONS[icon]} size={20} />
    </IconTile>
  );
}
