import { useRef, useState } from "react";

import { cx } from "@/shared/lib/cx";
import { motion, useSpring } from "@/shared/motion";

import { Button } from "./Button";
import { Icon, type IconName } from "./Icon";
import styles from "./ProofTile.module.css";
import { Sheet } from "./Sheet";

export type ProofKind = "photo" | "video";

/**
 * `uploading` sends with `progress`; `paused` waits (offline, or paused by a tap); `processing`
 * is a video being prepared; `failed` did not make it.
 */
export type ProofTileState = "ready" | "uploading" | "paused" | "processing" | "failed";

/**
 * One proof as a square thumbnail. Its state reads by shape, not only color: a ring filling while
 * it uploads, a pause mark while it waits, a clock while a video is prepared, an alert when it
 * failed, a play mark on a ready video. It fills its grid cell (`--proof-tile-size` caps tracks).
 * A video being prepared without a poster shows calm stripes (`--media-pending`). When `src`
 * fails to load it shows `fallbackSrc` (a video's phone thumbnail behind its poster), then the
 * placeholder.
 * With `onOpen` it is a button (view it, or pause and retry while uploading: the caller decides);
 * with `onRemove` it gets a remove button in the corner. Say the state in `label`.
 */
export function ProofTile({
  kind,
  state = "ready",
  src,
  fallbackSrc,
  progress = 0,
  label,
  onOpen,
  onRemove,
  removeLabel,
  duration,
  fill = false,
}: {
  kind: ProofKind;
  state?: ProofTileState;
  /** Thumbnail, poster, or the phone's local preview while uploading. */
  src?: string | null;
  /** Shown when `src` fails to load. */
  fallbackSrc?: string | null;
  /** 0 to 1, while uploading. */
  progress?: number;
  label: string;
  onOpen?: () => void;
  onRemove?: () => void;
  removeLabel?: string;
  /** A video's length, already formatted ("0:42"); shown in a pill at the bottom right. */
  duration?: string;
  /** Fill the cell's height instead of staying square (inside a `ProofMosaic`). */
  fill?: boolean;
}) {
  const [broken, setBroken] = useState<string[]>([]);
  const image = [src, fallbackSrc].find((url) => url && !broken.includes(url)) ?? null;
  const face = (
    <>
      {image ? (
        <img
          className={styles.image}
          src={image}
          alt=""
          loading="lazy"
          decoding="async"
          onError={() => setBroken((urls) => [...urls, image])}
        />
      ) : (
        <span className={styles.placeholder}>
          <Icon name={kind === "video" ? "video" : "image"} size={20} />
        </span>
      )}
      <Mark kind={kind} state={state} progress={progress} />
      {duration && state === "ready" && <span className={styles.duration}>{duration}</span>}
    </>
  );
  return (
    <span className={cx(styles.tile, styles[state], fill && styles.filled, !image && styles.empty)}>
      {onOpen ? (
        <button type="button" className={styles.face} onClick={onOpen} aria-label={label}>
          {face}
        </button>
      ) : (
        <span className={styles.face} role="img" aria-label={label}>
          {face}
        </span>
      )}
      {onRemove && (
        <button type="button" className={styles.remove} onClick={onRemove} aria-label={removeLabel}>
          <span className={styles.removeMark}>
            <Icon name="close" size={12} />
          </span>
        </button>
      )}
    </span>
  );
}

const MARKS: Partial<Record<ProofTileState, IconName>> = {
  paused: "pause",
  processing: "clock",
  failed: "alert",
};

function Mark({
  kind,
  state,
  progress,
}: {
  kind: ProofKind;
  state: ProofTileState;
  progress: number;
}) {
  const fill = useSpring("snappy");
  if (state === "uploading") {
    return (
      <span className={styles.mark}>
        <svg viewBox="0 0 40 40" className={styles.ring} aria-hidden="true">
          <circle cx="20" cy="20" r="16" className={styles.track} />
          <motion.circle
            cx="20"
            cy="20"
            r="16"
            transform="rotate(-90 20 20)"
            className={styles.fill}
            initial={false}
            animate={{ pathLength: Math.min(Math.max(progress, 0), 1) }}
            transition={fill}
          />
        </svg>
      </span>
    );
  }
  const icon = MARKS[state] ?? (kind === "video" ? "play" : undefined);
  if (!icon) return null;
  return (
    <span className={styles.mark}>
      <span className={styles.badge}>
        <Icon name={icon} size={16} />
      </span>
    </span>
  );
}

/** One kind of file the "+" tile can pick: `accept` is "image/*" or "video/*". */
export interface ProofChoice {
  label: string;
  accept: string;
  icon: IconName;
}

/**
 * The "+" tile: opens the phone's picker (camera or library) for one file. With one choice it
 * opens at once; with several (photo or video) a sheet titled `label` asks first, so each picker
 * takes one type: Chrome on Android hides videos from a picker that takes images too.
 */
export function ProofAddTile({
  choices,
  label,
  closeLabel,
  onPick,
  disabled = false,
}: {
  choices: ProofChoice[];
  label: string;
  closeLabel: string;
  onPick: (file: File) => void;
  disabled?: boolean;
}) {
  const inputs = useRef<(HTMLInputElement | null)[]>([]);
  const [asking, setAsking] = useState(false);
  const pick = (index: number) => inputs.current[index]?.click();
  return (
    <>
      <span className={styles.tile}>
        <button
          type="button"
          className={cx(styles.face, styles.add)}
          onClick={() => (choices.length > 1 ? setAsking(true) : pick(0))}
          aria-label={label}
          disabled={disabled}
        >
          <Icon name="plus" />
        </button>
        {choices.map((choice, i) => (
          <input
            key={choice.accept}
            ref={(element) => {
              inputs.current[i] = element;
            }}
            type="file"
            accept={choice.accept}
            hidden
            onChange={(event) => {
              const file = event.target.files?.[0];
              event.target.value = ""; // the same file can be picked again (to resume)
              if (file) onPick(file);
            }}
          />
        ))}
      </span>
      {choices.length > 1 && (
        <Sheet open={asking} onClose={() => setAsking(false)} title={label} closeLabel={closeLabel}>
          <div className={styles.choices}>
            {choices.map((choice, i) => (
              <Button
                key={choice.accept}
                variant="secondary"
                size="lg"
                fullWidth
                icon={<Icon name={choice.icon} />}
                onClick={() => {
                  pick(i); // inside the tap: browsers open pickers only from a user gesture
                  setAsking(false);
                }}
              >
                {choice.label}
              </Button>
            ))}
          </div>
        </Sheet>
      )}
    </>
  );
}
