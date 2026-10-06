import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import { api, putFile } from "@/api";
import type * as ApiModule from "@/api";
import { fail, ok } from "@/test/render";

import { cancel, partSize, retry, toggle, upload } from "./engine";
import { summary, useUploads } from "./store";

interface FakeFile {
  id: string;
  size: number;
  meta: Record<string, unknown>;
  s3Multipart?: { uploadId: string; key: string };
}
interface Hooks {
  limit: number;
  retryDelays: number[];
  getUploadParameters: (file: FakeFile) => unknown;
  listParts: (file: FakeFile) => unknown;
  signPart: (file: FakeFile, opts: { partNumber: number }) => Promise<unknown>;
  completeMultipartUpload: (file: FakeFile) => Promise<unknown>;
}
type Handler = (...args: unknown[]) => unknown;

// A stand-in for Uppy 5 that records the hooks the engine gives it and lets tests fire events.
const fake = vi.hoisted(() => {
  class FakeUppy {
    static instance: FakeUppy | undefined;
    hooks = {} as Hooks;
    files = new Map<string, FakeFile>();
    handlers = new Map<string, Handler[]>();
    upload = vi.fn(async () => undefined);
    pauseResume = vi.fn(() => true);
    retryUpload = vi.fn(async () => undefined);
    removeFile = vi.fn((id: string) => this.files.delete(id));
    constructor() {
      FakeUppy.instance = this;
    }
    use(_plugin: unknown, hooks: Hooks) {
      this.hooks = hooks;
      return this;
    }
    on(event: string, handler: Handler) {
      this.handlers.set(event, [...(this.handlers.get(event) ?? []), handler]);
      return this;
    }
    async emit(event: string, ...args: unknown[]) {
      for (const handler of this.handlers.get(event) ?? []) await handler(...args);
    }
    addFile(file: { data: Blob; meta: Record<string, unknown> }) {
      const id = `file-${this.files.size + 1}`;
      this.files.set(id, { id, size: file.data.size, meta: file.meta });
      return id;
    }
    setFileState(id: string, state: Partial<FakeFile>) {
      Object.assign(this.files.get(id) ?? {}, state);
    }
  }
  return { FakeUppy };
});

vi.mock("@uppy/core", () => ({ default: fake.FakeUppy }));
vi.mock("@uppy/aws-s3", () => ({ default: function AwsS3() {} }));
vi.mock("./media", () => ({
  fingerprint: (file: File) => `${file.name}|${file.size}`,
  preparePhoto: async () => ({
    body: new Blob(["small"], { type: "image/jpeg" }),
    contentType: "image/jpeg",
    thumb: new Blob(["t"], { type: "image/jpeg" }),
  }),
  prepareVideo: async (file: File) => ({
    body: file,
    contentType: "video/mp4",
    thumb: null,
    duration: 42,
  }),
}));
vi.mock("@/api", async (original) => ({
  ...(await original<typeof ApiModule>()),
  putFile: vi.fn(async () => undefined),
}));

const proof = (id: string, kind: "photo" | "video") => ({
  id,
  kind,
  status: "uploading" as const,
  url: null,
  hls_url: null,
  thumb_url: null,
  created_at: "2026-11-10T08:00:00Z",
});
const PHOTO_PLAN = {
  proof: proof("p1", "photo"),
  challenge_id: "walk",
  day: "2026-11-10",
  mode: "single" as const,
  content_type: "image/jpeg",
  put_url: "https://s3/put",
  part_size: null,
  part_count: null,
  parts: [],
  thumb_put_url: "https://s3/thumb",
};
const VIDEO_PLAN = {
  ...PHOTO_PLAN,
  proof: proof("v1", "video"),
  mode: "multipart" as const,
  content_type: "video/mp4",
  put_url: null,
  part_size: 16 * 1024 * 1024,
  part_count: 3,
  parts: [{ number: 1, etag: '"e1"' }],
  thumb_put_url: null,
};
const START = "/api/v1/challenges/{challenge_id}/check-ins/{day}/proofs";
const COMPLETE = "/api/v1/proofs/{proof_id}/complete";
const sentinel = { release: vi.fn(async () => undefined), addEventListener: vi.fn() };
const requestLock = vi.fn(async () => sentinel);

const uppy = () => fake.FakeUppy.instance as InstanceType<typeof fake.FakeUppy>;
const only = () => [...uppy().files.values()][0] as FakeFile;
const photo = () => new File(["x".repeat(10)], "a.heic", { type: "image/heic" });
const video = () => new File(["v".repeat(20)], "clip.mp4", { type: "video/mp4" });

function mockPost(plan: unknown = PHOTO_PLAN) {
  return vi.spyOn(api, "POST").mockImplementation(((path: string) => {
    if (path === START) return ok(plan, 201);
    if (path === COMPLETE) return ok({ ...PHOTO_PLAN.proof, status: "ready" });
    if (path === "/api/v1/proofs/{proof_id}/parts") {
      return ok({ parts: [{ number: 2, url: "https://s3/part2" }] });
    }
    return fail(404, { code: "not_found" });
  }) as never);
}

beforeAll(() => {
  URL.createObjectURL = vi.fn(() => "blob:preview");
  URL.revokeObjectURL = vi.fn();
  Object.defineProperty(navigator, "wakeLock", {
    value: { request: requestLock },
    configurable: true,
  });
});

beforeEach(() => {
  vi.restoreAllMocks();
  useUploads.setState({ items: {} });
  fake.FakeUppy.instance?.files.clear();
});

describe("upload engine", () => {
  it("sends a photo: started by the API, one PUT and a thumbnail, then completed", async () => {
    const post = mockPost();
    const onDone = vi.fn(async () => undefined);

    await upload({ challengeId: "walk", day: "2026-11-10", file: photo(), onDone });

    expect(post).toHaveBeenCalledWith(START, {
      params: { path: { challenge_id: "walk", day: "2026-11-10" } },
      body: {
        kind: "photo",
        content_type: "image/jpeg",
        size: 5,
        fingerprint: "",
        thumb_size: 1,
        duration: null,
      },
    });
    expect(putFile).toHaveBeenCalledWith("https://s3/thumb", expect.any(Blob), "image/jpeg");
    expect(uppy().hooks).toMatchObject({
      limit: 4,
      retryDelays: [1000, 2000, 4000, 8000, 16000, 32000],
    });
    const file = only();
    expect(uppy().hooks.getUploadParameters(file)).toEqual({
      method: "PUT",
      url: "https://s3/put",
      headers: { "Content-Type": "image/jpeg" },
    });
    expect(useUploads.getState().items[file.id]).toMatchObject({
      proofId: "p1",
      state: "uploading",
      preview: "blob:preview",
    });
    expect(uppy().upload).toHaveBeenCalled();

    await uppy().emit("upload-progress", file, { bytesUploaded: 2, bytesTotal: 5 });
    expect(useUploads.getState().items[file.id]?.progress).toBe(0.4);
    await uppy().emit("upload-success", file);

    expect(post).toHaveBeenCalledWith(COMPLETE, { params: { path: { proof_id: "p1" } } });
    expect(onDone).toHaveBeenCalled();
    expect(useUploads.getState().items).toEqual({});
  });

  it("resumes a video picked again: only the missing parts, each ETag reported first", async () => {
    vi.spyOn(api, "GET").mockImplementation((() => ok(VIDEO_PLAN)) as never);
    const post = mockPost();
    let land = () => undefined as unknown;
    const put = vi
      .spyOn(api, "PUT")
      .mockImplementation(
        (() => new Promise((resolve) => (land = () => resolve(ok(null, 204))))) as never,
      );

    await upload({
      challengeId: "walk",
      day: "2026-11-10",
      file: video(),
      onDone: async () => null,
    });

    expect(post).not.toHaveBeenCalledWith(START, expect.anything()); // resumed, not started
    const file = only();
    expect(file.s3Multipart).toEqual({ uploadId: "v1", key: "v1" });
    expect(uppy().hooks.listParts(file)).toEqual([{ PartNumber: 1, ETag: '"e1"' }]);
    expect(await uppy().hooks.signPart(file, { partNumber: 2 })).toEqual({
      method: "PUT",
      url: "https://s3/part2",
    });

    void uppy().emit("s3-multipart:part-uploaded", file, { PartNumber: 2, ETag: '"e2"' });
    const completing = uppy().hooks.completeMultipartUpload(file);
    await vi.waitFor(() => expect(put).toHaveBeenCalled());
    expect(post).not.toHaveBeenCalledWith(COMPLETE, expect.anything()); // waits for the report
    land();
    await completing;

    expect(put).toHaveBeenCalledWith("/api/v1/proofs/{proof_id}/parts/{number}", {
      params: { path: { proof_id: "v1", number: 2 } },
      body: { etag: '"e2"' },
    });
    expect(post).toHaveBeenCalledWith(COMPLETE, { params: { path: { proof_id: "v1" } } });
  });

  it("goes on with a video picked again while its upload is still here", async () => {
    vi.spyOn(api, "GET").mockImplementation((() => ok(VIDEO_PLAN)) as never);
    mockPost();
    const pick = () =>
      upload({ challengeId: "walk", day: "2026-11-10", file: video(), onDone: async () => null });
    await pick();
    await uppy().emit("upload-error", only());

    await pick();

    expect(uppy().files.size).toBe(1);
    expect(uppy().retryUpload).toHaveBeenCalledWith(only().id);
  });

  it("starts a new proof when the same video was begun for another challenge", async () => {
    vi.spyOn(api, "GET").mockImplementation((() =>
      ok({ ...VIDEO_PLAN, challenge_id: "read" })) as never);
    const post = mockPost(VIDEO_PLAN);

    await upload({
      challengeId: "walk",
      day: "2026-11-10",
      file: video(),
      onDone: async () => null,
    });

    expect(post).toHaveBeenCalledWith(
      START,
      expect.objectContaining({
        body: expect.objectContaining({
          kind: "video",
          fingerprint: "clip.mp4|20",
          thumb_size: null,
          duration: 42,
        }),
      }),
    );
  });

  it("lets the API's rules refuse before anything uploads", async () => {
    vi.spyOn(api, "POST").mockImplementation((() =>
      fail(409, { code: "too_many_proofs" })) as never);

    await expect(
      upload({ challengeId: "walk", day: "2026-11-10", file: photo(), onDone: async () => null }),
    ).rejects.toMatchObject({ code: "too_many_proofs" });

    expect(uppy().files.size).toBe(0);
    expect(useUploads.getState().items).toEqual({});
  });

  it("pauses offline, goes on online; a tap pauses; a failed one can be tried again", async () => {
    mockPost();
    await upload({
      challengeId: "walk",
      day: "2026-11-10",
      file: photo(),
      onDone: async () => null,
    });
    const id = only().id;
    const state = () => useUploads.getState().items[id]?.state;

    window.dispatchEvent(new Event("offline"));
    expect(state()).toBe("paused");
    window.dispatchEvent(new Event("online"));
    expect(state()).toBe("uploading");
    expect(uppy().pauseResume).toHaveBeenCalledTimes(2);

    await toggle(id);
    expect(state()).toBe("paused");
    await uppy().emit("upload-error", only());
    expect(state()).toBe("failed");
    await retry(id);
    expect(uppy().retryUpload).toHaveBeenCalledWith(id);
    expect(state()).toBe("uploading");
  });

  it("keeps the screen awake while something uploads", async () => {
    mockPost();
    await upload({
      challengeId: "walk",
      day: "2026-11-10",
      file: photo(),
      onDone: async () => null,
    });
    await vi.waitFor(() => expect(requestLock).toHaveBeenCalledWith("screen"));

    await cancel(only().id);

    await vi.waitFor(() => expect(sentinel.release).toHaveBeenCalled());
    expect(useUploads.getState().items).toEqual({});
  });

  it("cuts videos like the server does and sums progress by bytes", () => {
    expect(partSize(1024 ** 3 - 1)).toBe(16 * 1024 * 1024);
    expect(partSize(1024 ** 3)).toBe(64 * 1024 * 1024);
    const item = { proofId: "p", challengeId: "walk", kind: "photo" as const, preview: null };
    expect(
      summary({
        a: { ...item, id: "a", state: "uploading", progress: 0.5, size: 100 },
        b: { ...item, id: "b", state: "paused", progress: 0, size: 300 },
        c: { ...item, id: "c", state: "failed", progress: 0.9, size: 999 },
      }),
    ).toEqual({ count: 2, progress: 50 / 400 });
  });
});
