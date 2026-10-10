/**
 * The upload engine: our API decides, Uppy moves the bytes.
 *
 * 1. The subject's API starts the proof (its rules, at most 5, the day's deadline) or, for a video picked
 *    again, resumes it by fingerprint with the parts it already has.
 * 2. Uppy (v5; v6 drives S3 itself) sends the file straight to S3: one presigned PUT for a
 *    photo; a video's parts 4 at a time, each retried 6 times with backoff and signed afresh,
 *    each part's ETag reported to the API so a closed app can resume.
 * 3. Our API completes the proof once the bytes, the reports and the thumbnail are in.
 *
 * Uploads pause when the phone goes offline and go on when it is back; the screen stays awake
 * while anything uploads. Uppy loads only with the first upload.
 */
import type { Body, Meta, UppyFile } from "@uppy/core";

import { isApiError, putFile } from "@/api";

import { proofApi, type ProofSubject, type ProofUpload } from "../api";
import { fingerprint, prepareVideo, preparePhoto } from "./media";
import { summary, useUploads } from "./store";

const MiB = 1024 * 1024;
const GiB = 1024 * MiB;
const PARTS_AT_ONCE = 4;
const RETRY_DELAYS_MS = [1000, 2000, 4000, 8000, 16000, 32000]; // 6 retries, doubling

interface ProofMeta extends Meta {
  proofId: string;
  kind: "photo" | "video";
  contentType: string;
  putUrl: string | null;
  parts: { number: number; etag: string }[];
}
type ProofFile = UppyFile<ProofMeta, Body>;

/** Mirrors Upload.part_size on the server: 16 MiB under 1 GiB, 64 MiB above. */
export function partSize(size: number): number {
  return size < GiB ? 16 * MiB : 64 * MiB;
}

const reports = new Map<string, Promise<unknown>[]>(); // proof id -> ETag reports in flight
const thumbs = new Map<string, Promise<unknown>>(); // proof id -> thumbnail PUT
const done = new Map<string, (proofId: string) => Promise<unknown>>(); // file id -> refresh the screens
const offline = new Set<string>(); // files paused because the phone went offline

/** Report one part's ETag, retrying a little: resume depends on it. */
async function report(proofId: string, number: number, etag: string) {
  for (const wait of [0, 1000, 3000]) {
    await new Promise((resolve) => setTimeout(resolve, wait));
    try {
      await proofApi.reportPart(proofId, number, etag);
      return;
    } catch {
      // try again; complete reports a gap if it never lands
    }
  }
}

/** Everything sent: wait for the part reports and the thumbnail, then complete the proof. */
async function finish(proofId: string) {
  await Promise.allSettled([...(reports.get(proofId) ?? []), thumbs.get(proofId)]);
  reports.delete(proofId);
  thumbs.delete(proofId);
  await proofApi.complete(proofId);
}

let lock: WakeLockSentinel | null = null;

/** Keep the screen awake while anything uploads (the browser may say no: that is fine). */
async function holdScreen(active: boolean) {
  if (active && !lock && "wakeLock" in navigator) {
    lock = await navigator.wakeLock.request("screen").catch(() => null);
    lock?.addEventListener("release", () => (lock = null));
  } else if (!active && lock) {
    await lock.release().catch(() => undefined);
    lock = null;
  }
}

async function createUppy() {
  const [{ default: Uppy }, { default: AwsS3 }] = await Promise.all([
    import("@uppy/core"),
    import("@uppy/aws-s3"),
  ]);
  const store = useUploads.getState;
  const uppy = new Uppy<ProofMeta, Body>({ autoProceed: false, allowMultipleUploadBatches: true });
  uppy.use(AwsS3<ProofMeta, Body>, {
    limit: PARTS_AT_ONCE,
    retryDelays: RETRY_DELAYS_MS,
    shouldUseMultipart: (file) => file.meta.kind === "video",
    getChunkSize: (file) => partSize(file.size),
    getUploadParameters: (file) => ({
      method: "PUT",
      url: file.meta.putUrl ?? "",
      headers: { "Content-Type": file.meta.contentType },
    }),
    // Every video arrives with its upload already started by our API (see upload()).
    createMultipartUpload: () => Promise.reject(new Error("Start proofs through the API.")),
    listParts: (file) => file.meta.parts.map((p) => ({ PartNumber: p.number, ETag: p.etag })),
    signPart: async (file, { partNumber }) => ({
      method: "PUT",
      url: await proofApi.signPart(file.meta.proofId, partNumber),
    }),
    // Removing a proof deletes it (and stops its S3 upload) through our API.
    abortMultipartUpload: () => undefined,
    completeMultipartUpload: async (file) => {
      await finish(file.meta.proofId);
      return {};
    },
  });

  uppy.on("s3-multipart:part-uploaded", (file, part) => {
    // Uppy calls a photo's single PUT "part 1" too; only a video's parts are reported.
    if (!file || (file as ProofFile).meta.kind !== "video") return;
    const proofId = (file as ProofFile).meta.proofId;
    reports.set(proofId, [
      ...(reports.get(proofId) ?? []),
      report(proofId, part.PartNumber, part.ETag),
    ]);
  });
  uppy.on("upload-progress", (file, progress) => {
    if (file && progress.bytesTotal) {
      store().patch(file.id, { progress: (progress.bytesUploaded ?? 0) / progress.bytesTotal });
    }
  });
  uppy.on("upload-success", async (file) => {
    if (!file) return;
    try {
      if ((file as ProofFile).meta.kind === "photo") await finish((file as ProofFile).meta.proofId);
      await done.get(file.id)?.((file as ProofFile).meta.proofId);
      store().drop(file.id);
      done.delete(file.id);
      uppy.removeFile(file.id);
    } catch {
      store().patch(file.id, { state: "failed" });
    }
  });
  uppy.on("upload-error", (file) => {
    if (file) store().patch(file.id, { state: "failed" });
  });

  window.addEventListener("offline", () => {
    for (const item of Object.values(store().items)) {
      if (item.state !== "uploading") continue;
      offline.add(item.id);
      uppy.pauseResume(item.id);
      store().patch(item.id, { state: "paused" });
    }
  });
  window.addEventListener("online", () => {
    for (const id of offline) {
      if (store().items[id]?.state === "paused") {
        uppy.pauseResume(id);
        store().patch(id, { state: "uploading" });
      }
    }
    offline.clear();
  });
  useUploads.subscribe((state) => void holdScreen(summary(state.items).count > 0));
  document.addEventListener("visibilitychange", () => {
    // The browser drops the lock when the app is hidden; ask again when it is back.
    if (document.visibilityState === "visible") void holdScreen(summary(store().items).count > 0);
  });
  return uppy;
}

let engine: ReturnType<typeof createUppy> | null = null;
const uppy = () => (engine ??= createUppy());

/** Nothing to resume: start a new proof instead. */
function nothingToResume(error: unknown): null {
  if (isApiError(error) && error.status === 404) return null;
  throw error;
}

/**
 * Send a picked photo or video as proof for `subject` (today's check-in, a spin). Throws the API's
 * error (a day that is over, 5 already, a type it does not take) before anything uploads. `onDone`
 * refreshes the screens once the proof is complete (it gets the proof's id); the tile then comes
 * from the API.
 */
export async function upload({
  subject,
  file,
  onDone,
}: {
  subject: ProofSubject;
  file: File;
  onDone: (proofId: string) => Promise<unknown>;
}): Promise<void> {
  const kind = file.type.startsWith("video/") ? "video" : "photo";
  const prepared = kind === "video" ? await prepareVideo(file) : await preparePhoto(file);
  const print = fingerprint(file);
  let plan: ProofUpload | null =
    kind === "video" ? await subject.resume(print).catch(nothingToResume) : null;
  plan ??= await subject.start({
    kind,
    content_type: prepared.contentType,
    size: prepared.body.size,
    fingerprint: kind === "video" ? print : "",
    thumb_size: prepared.thumb?.size ?? null,
    duration: prepared.duration ?? null,
  });
  const proofId = plan.proof.id;
  if (plan.thumb_put_url && prepared.thumb) {
    thumbs.set(
      proofId,
      putFile(plan.thumb_put_url, prepared.thumb, "image/jpeg").catch(() => null),
    );
  }

  const running = Object.values(useUploads.getState().items).find((u) => u.proofId === proofId);
  if (running) {
    await retry(running.id); // the same video picked again while its upload is still here
    return;
  }

  const engine = await uppy();
  const id = engine.addFile({
    name: `${proofId}-${file.name}`, // Uppy refuses "duplicate" names: the same photo twice
    type: prepared.contentType,
    data: prepared.body,
    meta: {
      proofId,
      kind,
      contentType: prepared.contentType,
      putUrl: plan.put_url,
      parts: plan.parts,
    },
  });
  if (kind === "video") {
    // Uppy 5 reads this field (a restored upload) but does not declare it in its types.
    const restore = { s3Multipart: { uploadId: proofId, key: proofId } };
    engine.setFileState(id, restore as Partial<ProofFile>);
  }
  done.set(id, onDone);
  const shown = prepared.thumb ?? (kind === "photo" ? prepared.body : null);
  useUploads.getState().put({
    id,
    proofId,
    subject: subject.key,
    kind,
    preview: shown ? URL.createObjectURL(shown) : null,
    state: "uploading",
    progress: 0,
    size: prepared.body.size,
  });
  void engine.upload();
}

/** Pause a running upload, or go on with a paused one. */
export async function toggle(id: string): Promise<void> {
  const paused = (await uppy()).pauseResume(id);
  offline.delete(id);
  useUploads.getState().patch(id, { state: paused ? "paused" : "uploading" });
}

export async function retry(id: string): Promise<void> {
  useUploads.getState().patch(id, { state: "uploading" });
  await (await uppy()).retryUpload(id);
}

/** Stop an upload and forget it (its proof is deleted through the API by the caller). */
export async function cancel(id: string): Promise<void> {
  (await uppy()).removeFile(id);
  done.delete(id);
  offline.delete(id);
  useUploads.getState().drop(id);
}
