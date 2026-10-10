import { act, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "@/api";
import { ok, renderRoutes } from "@/test/render";

import { ProofTiles, type Proof, type ProofSubject } from ".";
import { toggle, upload } from "./uploads/engine";
import { useUploads } from "./uploads/store";

vi.mock("./uploads/engine", () => ({
  upload: vi.fn(async () => undefined),
  toggle: vi.fn(async () => undefined),
  retry: vi.fn(async () => undefined),
  cancel: vi.fn(async () => undefined),
}));

const GiB = 1024 ** 3;

const saved = (id: string, kind: Proof["kind"], status: Proof["status"]): Proof => ({
  id,
  kind,
  status,
  url: status === "ready" || status === "processing" ? `/media/${id}` : null,
  hls_url: null,
  thumb_url: kind === "photo" ? `/media/${id}-thumb.jpg` : null,
  phone_thumb_url: null,
  created_at: "2026-11-10T08:00:00Z",
  duration: null,
  posted: false, // a draft file: removable until posted
});

const walk: ProofSubject = { key: "check-in:walk", start: vi.fn(), resume: vi.fn() };
const onChanged = vi.fn(async () => undefined);

function show(
  proofs: Proof[] = [saved("p1", "photo", "ready"), saved("v1", "video", "processing")],
) {
  return renderRoutes([
    {
      path: "/",
      element: <ProofTiles subject={walk} title="Walk" proofs={proofs} onChanged={onChanged} />,
    },
  ]);
}

beforeEach(() => {
  vi.clearAllMocks();
  useUploads.setState({ items: {} });
});
afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("proof tiles", () => {
  it("shows the saved proofs and + with one picker per kind; a pick uploads to the subject", async () => {
    const { container } = show();

    expect(await screen.findByRole("button", { name: "Photo. Tap to open" })).toBeInTheDocument();
    // Processing, but its original already plays: it opens too.
    expect(screen.getByRole("button", { name: "Video, being prepared" })).toBeInTheDocument();
    // One picker per kind: Chrome on Android hides videos from a picker that takes images too.
    const inputs = container.querySelectorAll<HTMLInputElement>('input[type="file"]');
    expect([...inputs].map((i) => i.accept)).toEqual(["image/*", "video/*"]);

    const file = new File(["jpg"], "walk.jpg", { type: "image/jpeg" });
    await userEvent.upload(inputs[0] as HTMLInputElement, file);

    expect(upload).toHaveBeenCalledWith({ subject: walk, file, onDone: expect.any(Function) });
  });

  it("shows this phone's uploads with their progress; a tap pauses", async () => {
    useUploads.getState().put({
      id: "up1",
      proofId: "p9",
      subject: "check-in:walk",
      kind: "photo",
      preview: null,
      state: "uploading",
      progress: 0.4,
      size: 100,
    });
    show();

    await userEvent.click(
      await screen.findByRole("button", { name: "Photo, 40% uploaded. Tap to pause" }),
    );
    expect(toggle).toHaveBeenCalledWith("up1");
  });

  it("removes a proof after the undo time, and not at all when undone", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const del = vi.spyOn(api, "DELETE").mockImplementation((() => ok(null, 204)) as never);
    show();

    const [first] = await screen.findAllByRole("button", { name: "Remove this proof" });
    await userEvent.click(first as HTMLElement);
    expect(screen.queryByRole("button", { name: "Photo. Tap to open" })).toBeNull();
    await userEvent.click(await screen.findByRole("button", { name: "Undo" }));
    expect(await screen.findByRole("button", { name: "Photo. Tap to open" })).toBeInTheDocument();
    await act(() => vi.advanceTimersByTimeAsync(5000));
    expect(del).not.toHaveBeenCalled();

    const [again] = screen.getAllByRole("button", { name: "Remove this proof" });
    await userEvent.click(again as HTMLElement);
    await act(() => vi.advanceTimersByTimeAsync(5000));
    expect(del).toHaveBeenCalledWith("/api/v1/proofs/{proof_id}", {
      params: { path: { proof_id: "p1" } },
    });
  });

  it("offers no + once the next post has five files (failed ones do not count)", async () => {
    const five = ["a", "b", "c", "d", "e"].map((id) => saved(id, "photo", "ready"));
    show([...five, saved("f", "photo", "failed")]);

    expect(await screen.findAllByRole("button", { name: "Photo. Tap to open" })).toHaveLength(5);
    expect(screen.queryByRole("button", { name: "Add a photo or video" })).toBeNull();
  });

  it("keeps posted proofs: no remove, and the next post takes five more", async () => {
    const posted = ["a", "b", "c", "d", "e"].map((id) => ({
      ...saved(id, "photo", "ready"),
      posted: true,
    }));
    show(posted);

    expect(await screen.findAllByRole("button", { name: "Photo. Tap to open" })).toHaveLength(5);
    expect(screen.queryByRole("button", { name: "Remove this proof" })).toBeNull();
    expect(screen.getByRole("button", { name: "Add a photo or video" })).toBeInTheDocument();
  });

  it("opens a saved proof full screen", async () => {
    show();
    await userEvent.click(await screen.findByRole("button", { name: "Photo. Tap to open" }));

    const viewer = await screen.findByRole("dialog", { name: "Proofs" });
    expect(within(viewer).getByText("1 / 2")).toBeInTheDocument();
  });

  it("asks before uploading a very large video on a phone", async () => {
    Object.defineProperty(window, "matchMedia", {
      value: () => ({ matches: true }), // a phone
      configurable: true,
    });
    const { container } = show();
    await screen.findByRole("button", { name: "Photo. Tap to open" });
    const big = new File(["v"], "trip.mp4", { type: "video/mp4" });
    Object.defineProperty(big, "size", { value: 3.1 * GiB });

    await userEvent.upload(
      container.querySelector('input[accept="video/*"]') as HTMLInputElement,
      big,
    );
    expect(upload).not.toHaveBeenCalled();
    expect(await screen.findByText("Upload 3.1 GB?")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Upload it" }));

    expect(upload).toHaveBeenCalledWith(expect.objectContaining({ file: big }));
  });
});
