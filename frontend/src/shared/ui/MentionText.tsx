import { Link } from "react-router";

import { findMentions, type Person, type Segment } from "@/shared/lib/mentions";

import styles from "./MentionText.module.css";

/**
 * A comment's text with its mentions as chips: `@Name` opens that member's page, `@all` is a
 * chip alone. The rest is the text as typed.
 */
export function MentionText({ text, people }: { text: string; people: Person[] }) {
  return <>{findMentions(text, people).map(piece)}</>;
}

function piece(part: Segment, index: number) {
  if (part.member) {
    return (
      <Link key={index} to={`/crew/members/${part.member.id}`} className={styles.chip}>
        {part.text}
      </Link>
    );
  }
  if (part.all) {
    return (
      <span key={index} className={styles.chip}>
        {part.text}
      </span>
    );
  }
  return part.text;
}
