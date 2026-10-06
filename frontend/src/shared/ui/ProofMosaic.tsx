import { cx } from "@/shared/lib/cx";

import styles from "./ProofMosaic.module.css";
import { ProofTile, type ProofKind, type ProofTileState } from "./ProofTile";

export type FeedProof = {
  key: string;
  kind: ProofKind;
  state: ProofTileState;
  src?: string | null;
  /** The full photo, for the big tiles: a thumbnail is too small there and looks blurred. */
  full?: string | null;
  label: string;
  /** A video's length, formatted ("0:42"). */
  duration?: string;
};

/** The mosaic shows three proofs; the third carries "+N" for the rest. */
const SHOWN = 3;

/**
 * A check-in's proofs laid out by count: one fills a 4:3 box; two sit side by side; three or
 * more show one big and two small, with "+N" over the third. The big tiles (one, both of two,
 * the first of three) show `full` when there is one; the small ones keep the thumbnail. Tiles meet with
 * `--radius-media-inner`; the outer corners stay `--radius-sm`. Tapping a tile opens the viewer
 * at that proof; "+N" opens it at the first one hidden.
 */
export function ProofMosaic({
  proofs,
  onOpen,
  moreLabel,
}: {
  proofs: FeedProof[];
  onOpen?: (index: number) => void;
  /** Accessible name of "+N": "2 more proofs". */
  moreLabel?: string;
}) {
  if (proofs.length === 0) return null;
  const shown = proofs.slice(0, SHOWN);
  const more = proofs.length - shown.length;
  const layout = shown.length === 1 ? styles.one : shown.length === 2 ? styles.two : styles.three;
  return (
    <div className={cx(styles.mosaic, layout)}>
      {shown.map((proof, i) => (
        <span key={proof.key} className={cx(styles.cell, i === 0 && styles.first)}>
          <ProofTile
            fill
            kind={proof.kind}
            state={proof.state}
            src={(i === 0 || shown.length === 2) && proof.full ? proof.full : proof.src}
            label={proof.label}
            duration={proof.duration}
            onOpen={onOpen && (() => onOpen(i))}
          />
          {more > 0 && i === SHOWN - 1 && (
            <button
              type="button"
              className={styles.more}
              onClick={() => onOpen?.(SHOWN)}
              disabled={!onOpen}
              aria-label={moreLabel}
            >
              {`+${more}`}
            </button>
          )}
        </span>
      ))}
    </div>
  );
}
