import { useTranslation } from "react-i18next";

import type { Member } from "@/api";
import { motion, staggerStep, useSpring, variants } from "@/shared/motion";
import { Avatar, StatusPill } from "@/shared/ui";

import styles from "../crew.module.css";

/** Members in rotation order. Pops them in one after another. */
export function MemberList({ members, meId }: { members: Member[]; meId?: string }) {
  const { t } = useTranslation();
  const spring = useSpring("bouncy");
  return (
    <motion.ol
      className={styles.list}
      initial="hidden"
      animate="visible"
      transition={{ staggerChildren: staggerStep }}
    >
      {members.map((member) => (
        <motion.li
          key={member.id}
          className={styles.row}
          variants={variants.popIn}
          transition={spring}
        >
          <span className={styles.position}>{member.rotation_position + 1}</span>
          <Avatar name={member.display_name} seed={member.avatar_seed} />
          <span className={styles.name}>{member.display_name}</span>
          {member.id === meId && <StatusPill tone="accent">{t("crew.you")}</StatusPill>}
          {member.role === "admin" && <StatusPill>{t("crew.admin")}</StatusPill>}
        </motion.li>
      ))}
    </motion.ol>
  );
}
