import { useRef } from "react";

import { cx } from "@/shared/lib/cx";
import { motion, useSpring } from "@/shared/motion";

import { Icon, type IconName } from "./Icon";
import styles from "./ProofTile.module.css";

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
 * With `onOpen` it is a button (view it, or pause and retry while uploading: the caller decides);
 * with `onRemove` it gets a remove button in the corner. Say the state in `label`.
 */
export function ProofTile({
  kind,
  state = "ready",
  src,
  progress = 0,
  label,
  onOpen,
  onRemove,
  removeLabel,
}: {
  kind: ProofKind;
  state?: ProofTileState;
  /** Thumbnail, poster, or the phone's local preview while uploading. */
  src?: string | null;
  /** 0 to 1, while uploading. */
  progress?: number;
  label: string;
  onOpen?: () => void;
  onRemove?: () => void;
  removeLabel?: string;
}) {
  const face = (
    <>
      {src ? (
        <img className={styles.image} src={src} alt="" loading="lazy" decoding="async" />
      ) : (
        <span className={styles.placeholder}>
          <Icon name={kind === "video" ? "video" : "image"} size={20} />
        </span>
      )}
      <Mark kind={kind} state={state} progress={progress} />
    </>
  );
  return (
    <span className={cx(styles.tile, styles[state])}>
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

/**
 * The "+" tile: opens the phone's picker (camera or library) for one file of the `accept` types
 * ("image/*", "video/*", or both).
 */
export function ProofAddTile({
  accept,
  label,
  onPick,
  disabled = false,
}: {
  accept: string;
  label: string;
  onPick: (file: File) => void;
  disabled?: boolean;
}) {
  const input = useRef<HTMLInputElement>(null);
  return (
    <span className={styles.tile}>
      <button
        type="button"
        className={cx(styles.face, styles.add)}
        onClick={() => input.current?.click()}
        aria-label={label}
        disabled={disabled}
      >
        <Icon name="plus" />
      </button>
      <input
        ref={input}
        type="file"
        accept={accept}
        hidden
        onChange={(event) => {
          const file = event.target.files?.[0];
          event.target.value = ""; // the same file can be picked again (to resume)
          if (file) onPick(file);
        }}
      />
    </span>
  );
}
