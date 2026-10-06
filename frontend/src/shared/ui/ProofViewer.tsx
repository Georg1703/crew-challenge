import { useCallback, useEffect, useRef, useState, type PointerEvent } from "react";

import { cx } from "@/shared/lib/cx";
import { AnimatePresence, motion, useSpring } from "@/shared/motion";

import { Icon } from "./Icon";
import styles from "./ProofViewer.module.css";

export type ViewerItem = {
  key: string;
  kind: "photo" | "video";
  /** The full photo, or the original video (played as is when there is no HLS playlist). */
  src: string;
  /** A transcoded video's HLS playlist (production). */
  hlsSrc?: string | null;
  poster?: string | null;
  /** Shown at the top and read by screen readers: "Ana, Walk, Monday 5 October". */
  caption: string;
};

const SWIPE_PX = 80;
const SWIPE_SPEED = 500;
const MAX_ZOOM = 4;
const DOUBLE_TAP_ZOOM = 2.5;

const SLIDE = {
  enter: (direction: number) => ({ x: `${direction * 100}%`, opacity: 0 }),
  center: { x: 0, opacity: 1 },
  exit: (direction: number) => ({ x: `${direction * -100}%`, opacity: 0 }),
};

/**
 * Proofs full screen, one at a time: swipe, the arrows or the arrow keys move between them;
 * Escape or the close button leaves. Photos zoom with a pinch or a double tap; videos play
 * inline with sound, from the HLS playlist when there is one (hls.js loads only where
 * the browser cannot play HLS itself, and the original plays if the playlist fails).
 */
export function ProofViewer({
  items,
  index,
  onIndexChange,
  open,
  onClose,
  label,
  closeLabel,
  previousLabel,
  nextLabel,
}: {
  items: ViewerItem[];
  index: number;
  onIndexChange: (index: number) => void;
  open: boolean;
  onClose: () => void;
  /** The dialog's name ("Proofs"). */
  label: string;
  closeLabel: string;
  previousLabel: string;
  nextLabel: string;
}) {
  const panel = useRef<HTMLDivElement>(null);
  const [direction, setDirection] = useState(0);
  const [zoomed, setZoomed] = useState(false);
  const fade = useSpring("gentle");
  const slide = useSpring("snappy");
  const item = items[index];

  const go = useCallback(
    (step: number) => {
      const next = index + step;
      if (next < 0 || next >= items.length) return;
      setDirection(step);
      setZoomed(false);
      onIndexChange(next);
    },
    [index, items.length, onIndexChange],
  );

  useEffect(() => {
    if (!open) return;
    const previous = document.activeElement as HTMLElement | null;
    panel.current?.focus();
    return () => previous?.focus();
  }, [open]);

  useEffect(() => {
    if (!open) return;
    // Capture phase: the viewer sits above a sheet it may open from; it closes alone.
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
      } else if (event.key === "ArrowRight") go(1);
      else if (event.key === "ArrowLeft") go(-1);
    };
    document.addEventListener("keydown", onKey, true);
    return () => document.removeEventListener("keydown", onKey, true);
  }, [open, onClose, go]);

  return (
    <AnimatePresence>
      {open && item && (
        <motion.div
          ref={panel}
          className={styles.root}
          role="dialog"
          aria-modal="true"
          aria-label={label}
          tabIndex={-1}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={fade}
        >
          <header className={styles.bar}>
            <p className={styles.caption}>{item.caption}</p>
            {items.length > 1 && (
              <span className={styles.count}>{`${index + 1} / ${items.length}`}</span>
            )}
            <button type="button" className={styles.icon} onClick={onClose} aria-label={closeLabel}>
              <Icon name="close" />
            </button>
          </header>
          <div className={styles.stage}>
            <AnimatePresence initial={false} custom={direction}>
              <motion.div
                key={item.key}
                className={styles.slide}
                custom={direction}
                variants={SLIDE}
                initial="enter"
                animate="center"
                exit="exit"
                transition={slide}
                drag={zoomed || items.length < 2 ? false : "x"}
                dragConstraints={{ left: 0, right: 0 }}
                dragElastic={0.6}
                onDragEnd={(_event, info) => {
                  if (info.offset.x < -SWIPE_PX || info.velocity.x < -SWIPE_SPEED) go(1);
                  else if (info.offset.x > SWIPE_PX || info.velocity.x > SWIPE_SPEED) go(-1);
                }}
              >
                {item.kind === "video" ? (
                  <Video item={item} />
                ) : (
                  <ZoomablePhoto src={item.src} alt={item.caption} onZoom={setZoomed} />
                )}
              </motion.div>
            </AnimatePresence>
            {index > 0 && (
              <button
                type="button"
                className={cx(styles.icon, styles.previous)}
                onClick={() => go(-1)}
                aria-label={previousLabel}
              >
                <Icon name="chevronLeft" />
              </button>
            )}
            {index < items.length - 1 && (
              <button
                type="button"
                className={cx(styles.icon, styles.next)}
                onClick={() => go(1)}
                aria-label={nextLabel}
              >
                <Icon name="chevronRight" />
              </button>
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

/** Whether videos play with sound; muting one keeps the next ones muted until unmuted. */
let withSound = true;

/**
 * Starts a video with sound: opening the viewer is a tap, which browsers accept for sound. If one
 * still refuses (iOS sometimes does after hls.js loads), it plays muted and the controls unmute.
 */
function start(video: HTMLVideoElement) {
  video.muted = !withSound;
  void video.play()?.catch(() => {
    if (video.muted) return;
    video.muted = true;
    void video.play()?.catch(() => undefined);
  });
}

/** Plays HLS where possible (natively, or with hls.js loaded on demand), else the original. */
function Video({ item }: { item: ViewerItem }) {
  const ref = useRef<HTMLVideoElement>(null);
  const { src, hlsSrc } = item;

  useEffect(() => {
    const video = ref.current;
    if (!video) return;
    if (!hlsSrc || video.canPlayType("application/vnd.apple.mpegurl")) {
      video.src = hlsSrc ?? src;
      start(video);
      return;
    }
    let player: { destroy: () => void } | undefined;
    let gone = false;
    void import("hls.js").then(({ default: Hls }) => {
      if (gone) return;
      if (!Hls.isSupported()) {
        video.src = src;
        start(video);
        return;
      }
      // Playlists and segments come from CloudFront with the crew's signed cookies.
      const hls = new Hls({
        xhrSetup: (xhr) => {
          xhr.withCredentials = true;
        },
      });
      hls.on(Hls.Events.ERROR, (_event, data) => {
        if (!data.fatal) return;
        hls.destroy();
        video.src = src;
      });
      hls.loadSource(hlsSrc);
      hls.attachMedia(video);
      start(video);
      player = hls;
    });
    return () => {
      gone = true;
      player?.destroy();
    };
  }, [src, hlsSrc]);

  return (
    <video
      ref={ref}
      className={styles.media}
      poster={item.poster ?? undefined}
      aria-label={item.caption}
      controls
      playsInline
      preload="metadata"
      onVolumeChange={(event) => {
        // Only a person changes it while it plays; the fallback above mutes before playing.
        if (!event.currentTarget.paused) withSound = !event.currentTarget.muted;
      }}
    />
  );
}

/** A photo that zooms with a pinch or a double tap, and pans while zoomed. */
function ZoomablePhoto({
  src,
  alt,
  onZoom,
}: {
  src: string;
  alt: string;
  onZoom: (zoomed: boolean) => void;
}) {
  const [view, setView] = useState({ scale: 1, x: 0, y: 0 });
  const pointers = useRef(new Map<number, { x: number; y: number }>());
  const pinch = useRef<{ distance: number; scale: number } | null>(null);
  const zoomed = view.scale > 1;

  useEffect(() => onZoom(zoomed), [zoomed, onZoom]);

  const spread = () => {
    const [a, b] = [...pointers.current.values()];
    return a && b ? Math.hypot(a.x - b.x, a.y - b.y) : 0;
  };

  const down = (event: PointerEvent) => {
    pointers.current.set(event.pointerId, { x: event.clientX, y: event.clientY });
    if (pointers.current.size === 2) pinch.current = { distance: spread(), scale: view.scale };
  };

  const move = (event: PointerEvent) => {
    const last = pointers.current.get(event.pointerId);
    if (!last) return;
    pointers.current.set(event.pointerId, { x: event.clientX, y: event.clientY });
    if (pinch.current && pinch.current.distance > 0 && pointers.current.size === 2) {
      const ratio = spread() / pinch.current.distance;
      const scale = Math.min(Math.max(pinch.current.scale * ratio, 1), MAX_ZOOM);
      setView((v) => (scale === 1 ? { scale, x: 0, y: 0 } : { ...v, scale }));
    } else if (zoomed) {
      const dx = event.clientX - last.x;
      const dy = event.clientY - last.y;
      setView((v) => ({ ...v, x: v.x + dx, y: v.y + dy }));
    }
  };

  const up = (event: PointerEvent) => {
    pointers.current.delete(event.pointerId);
    if (pointers.current.size < 2) pinch.current = null;
  };

  return (
    <div
      className={styles.zoom}
      data-zoomed={zoomed || undefined}
      onPointerDown={down}
      onPointerMove={move}
      onPointerUp={up}
      onPointerCancel={up}
      onDoubleClick={() =>
        setView(zoomed ? { scale: 1, x: 0, y: 0 } : { scale: DOUBLE_TAP_ZOOM, x: 0, y: 0 })
      }
    >
      <img
        className={styles.media}
        src={src}
        alt={alt}
        draggable={false}
        style={{ transform: `translate(${view.x}px, ${view.y}px) scale(${view.scale})` }}
      />
    </div>
  );
}
