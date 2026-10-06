import { afterEach, describe, expect, it, vi } from "vitest";

import { putFile } from "./upload";

const NO_WAIT = [0, 0, 0];

afterEach(() => vi.restoreAllMocks());

describe("putFile", () => {
  it("PUTs the file with its content type", async () => {
    const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(null));
    const body = new Blob(["jpg"], { type: "image/jpeg" });

    await putFile("https://s3/thumb", body, "image/jpeg", NO_WAIT);

    expect(fetch).toHaveBeenCalledWith("https://s3/thumb", {
      method: "PUT",
      body,
      headers: { "Content-Type": "image/jpeg" },
    });
  });

  it("tries again after a network error or a 5xx, not after a 4xx", async () => {
    const fetch = vi
      .spyOn(globalThis, "fetch")
      .mockRejectedValueOnce(new TypeError("offline"))
      .mockResolvedValueOnce(new Response(null, { status: 503 }))
      .mockResolvedValueOnce(new Response(null));
    await putFile("https://s3/thumb", new Blob(["x"]), "image/jpeg", NO_WAIT);
    expect(fetch).toHaveBeenCalledTimes(3);

    fetch.mockReset().mockResolvedValue(new Response(null, { status: 403 }));
    await expect(
      putFile("https://s3/thumb", new Blob(["x"]), "image/jpeg", NO_WAIT),
    ).rejects.toMatchObject({ status: 403, code: "upload_failed" });
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it("gives up after its retries", async () => {
    const fetch = vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("offline"));
    await expect(
      putFile("https://s3/thumb", new Blob(["x"]), "image/jpeg", NO_WAIT),
    ).rejects.toMatchObject({ status: 0, code: "upload_failed" });
    expect(fetch).toHaveBeenCalledTimes(4);
  });
});
