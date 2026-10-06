import { Avatar } from "./Avatar";
import styles from "./FeedItem.module.css";
import { ProofTile, type ProofKind, type ProofTileState } from "./ProofTile";

export type FeedProof = {
  key: string;
  kind: ProofKind;
  state: ProofTileState;
  src?: string | null;
  label: string;
};

const SHOWN = 3;

/**
 * One check-in in the crew's feed, as an item of a `List`: who did what and when, then up to
 * three proofs and "+N". Tapping a proof (or "+N") opens it at that position.
 */
export function FeedItem({
  name,
  seed,
  text,
  time,
  proofs = [],
  onOpenProof,
  moreLabel,
}: {
  name: string;
  seed: string;
  /** "Ana checked in Walk", "Bogdan read 20 pages". */
  text: string;
  /** "5 min ago", "yesterday 21:40", formatted by the caller. */
  time: string;
  proofs?: FeedProof[];
  onOpenProof?: (index: number) => void;
  /** Accessible name of "+N": "2 more proofs". */
  moreLabel?: string;
}) {
  const shown = proofs.slice(0, SHOWN);
  const more = proofs.length - shown.length;
  return (
    <li className={styles.item}>
      <Avatar name={name} seed={seed} />
      <div className={styles.body}>
        <p className={styles.text}>{text}</p>
        <p className={styles.time}>{time}</p>
        {proofs.length > 0 && (
          <div className={styles.proofs}>
            {shown.map((proof, i) => (
              <ProofTile
                key={proof.key}
                kind={proof.kind}
                state={proof.state}
                src={proof.src}
                label={proof.label}
                onOpen={onOpenProof && (() => onOpenProof(i))}
              />
            ))}
            {more > 0 && (
              <button
                type="button"
                className={styles.more}
                onClick={() => onOpenProof?.(SHOWN)}
                disabled={!onOpenProof}
                aria-label={moreLabel}
              >
                {`+${more}`}
              </button>
            )}
          </div>
        )}
      </div>
    </li>
  );
}
