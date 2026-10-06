/**
 * Straight-to-storage PUTs for small files (a proof's thumbnail). Files never pass through
 * Django: the presigned URL from the API carries the permission. Big files go through the upload
 * engine in features/checkins/uploads instead (Uppy, multipart).
 */
import { ApiError } from "./errors";

const RETRY_DELAYS_MS = [1000, 2000, 4000];

/** PUT a file to a presigned URL, retrying network errors and 5xx answers. */
export async function putFile(
  url: string,
  body: Blob,
  contentType: string,
  delays: readonly number[] = RETRY_DELAYS_MS,
): Promise<void> {
  for (let attempt = 0; ; attempt++) {
    let response: Response | undefined;
    try {
      response = await globalThis.fetch(url, {
        method: "PUT",
        body,
        headers: { "Content-Type": contentType },
      });
    } catch {
      response = undefined; // offline or DNS: try again
    }
    if (response?.ok) return;
    const delay = delays[attempt];
    if ((response && response.status < 500) || delay === undefined) {
      throw new ApiError(response?.status ?? 0, {
        code: "upload_failed",
        message: "The file could not be uploaded.",
      });
    }
    await new Promise((resolve) => setTimeout(resolve, delay));
  }
}
