/**
 * Getting a picked file ready on the phone: photos shrink to at most 2048 px (JPEG ~0.8, usually
 * 300-700 KB instead of 3-8 MB) with a 480 px thumbnail; videos go as they are, with a poster
 * frame as their thumbnail. Anything the browser cannot decode goes as it is, without a thumbnail.
 */
const PHOTO_MAX_PX = 2048;
const THUMB_MAX_PX = 480;
const JPEG_QUALITY = 0.8;
const POSTER_WAIT_MS = 5000;

export interface Prepared {
  body: Blob;
  contentType: string;
  thumb: Blob | null;
  /** A video's length in whole seconds, when the phone could read it. */
  duration?: number | null;
}

/** The API takes 1 second to 3 hours; anything else stays unknown. */
const MAX_SECONDS = 3 * 60 * 60;

function seconds(value: number): number | null {
  const whole = Math.round(value);
  return Number.isFinite(value) && whole >= 1 && whole <= MAX_SECONDS ? whole : null;
}

/** name|size|lastModified: picking the same file again finds its unfinished upload. */
export function fingerprint(file: File): string {
  return `${file.name}|${file.size}|${file.lastModified}`;
}

function draw(source: CanvasImageSource, width: number, height: number, max: number) {
  const scale = Math.min(1, max / Math.max(width, height));
  const canvas = document.createElement("canvas");
  canvas.width = Math.max(1, Math.round(width * scale));
  canvas.height = Math.max(1, Math.round(height * scale));
  const context = canvas.getContext("2d");
  if (!context) throw new Error("No 2D canvas.");
  context.drawImage(source, 0, 0, canvas.width, canvas.height);
  return new Promise<Blob>((resolve, reject) =>
    canvas.toBlob(
      (blob) => (blob ? resolve(blob) : reject(new Error("toBlob"))),
      "image/jpeg",
      JPEG_QUALITY,
    ),
  );
}

export async function preparePhoto(file: File): Promise<Prepared> {
  try {
    const image = await createImageBitmap(file, { imageOrientation: "from-image" });
    try {
      const body = await draw(image, image.width, image.height, PHOTO_MAX_PX);
      const thumb = await draw(image, image.width, image.height, THUMB_MAX_PX);
      return { body, contentType: "image/jpeg", thumb };
    } finally {
      image.close();
    }
  } catch {
    return { body: file, contentType: file.type, thumb: null }; // e.g. HEIC in Chrome
  }
}

function once(target: HTMLMediaElement, event: string, ms: number) {
  return new Promise<void>((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error(`No ${event}`)), ms);
    target.addEventListener(event, () => (clearTimeout(timer), resolve()), { once: true });
    target.addEventListener("error", () => (clearTimeout(timer), reject(new Error("error"))), {
      once: true,
    });
  });
}

export async function prepareVideo(file: File, wait = POSTER_WAIT_MS): Promise<Prepared> {
  const url = URL.createObjectURL(file);
  let thumb: Blob | null = null;
  let duration: number | null = null;
  try {
    const video = document.createElement("video");
    video.muted = true;
    video.playsInline = true;
    video.preload = "auto";
    video.src = url;
    await once(video, "loadeddata", wait);
    duration = seconds(video.duration);
    video.currentTime = Math.min(0.1, video.duration || 0);
    await once(video, "seeked", wait);
    thumb = await draw(video, video.videoWidth, video.videoHeight, THUMB_MAX_PX);
  } catch {
    thumb = null; // the phone cannot decode it here: the server's poster comes later
  } finally {
    URL.revokeObjectURL(url);
  }
  return { body: file, contentType: file.type, thumb, duration };
}
