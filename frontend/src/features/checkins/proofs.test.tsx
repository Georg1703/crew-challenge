import { act, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "@/api";
import { TabBar } from "@/shared/ui";
import { bogdan, meAs } from "@/test/fixtures";
import { fail, ok, renderRoutes } from "@/test/render";

import { TodayCheckIns, useCheckInAction } from ".";
import type { Proof, Today, TodayChallenge } from "./api";
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
  created_at: "2026-11-10T08:00:00Z",
  duration: null,
});

const walk: TodayChallenge = {
  id: "walk",
  title: "Walk",
  icon: "walk",
  measure: "check",
  unit: "",
  window: "day",
  need_kind: "count",
  need_value: 1,
  day_min: null,
  proof_required: true,
  end_date: "2026-11-30",
  state: "done",
  total: null,
  streak: 1,
  week: [],
  current: null,
  settled: true,
  proofs: [saved("p1", "photo", "ready"), saved("v1", "video", "processing")],
  proof_days: ["2026-11-10"],
};

const today = (card: TodayChallenge): Today => ({
  day: "2026-11-10",
  deadline: "2026-11-10T22:00:00Z",
  challenges: [card],
  crew: [],
});

function show(card: TodayChallenge = walk) {
  vi.spyOn(api, "GET").mockImplementation(((path: string) => {
    if (path === "/api/v1/me") return ok(meAs(bogdan));
    if (path === "/api/v1/today") return ok(today(card));
    return fail(404, { code: "not_found" });
  }) as never);
  return renderRoutes([{ path: "/", element: <TodayCheckIns /> }]);
}

beforeEach(() => {
  vi.clearAllMocks();
  useUploads.setState({ items: {} });
});
afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("proofs on today's card", () => {
  it("shows the day's proofs after the check-in, and + to pick more of the kinds it takes", async () => {
    const { container } = show();

    expect(await screen.findByRole("button", { name: "Photo. Tap to open" })).toBeInTheDocument();
    // Processing, but its original already plays: it opens too.
    expect(screen.getByRole("button", { name: "Video, being prepared" })).toBeInTheDocument();
    // One picker per kind: Chrome on Android hides videos from a picker that takes images too.
    const inputs = container.querySelectorAll<HTMLInputElement>('input[type="file"]');
    expect([...inputs].map((i) => i.accept)).toEqual(["image/*", "video/*"]);

    const file = new File(["jpg"], "walk.jpg", { type: "image/jpeg" });
    await userEvent.upload(inputs[0] as HTMLInputElement, file);

    expect(upload).toHaveBeenCalledWith(
      expect.objectContaining({ challengeId: "walk", day: "2026-11-10", file }),
    );
  });

  it("nudges for proof when the challenge asks for it", async () => {
    show({ ...walk, proofs: [] });
    expect(await screen.findByText("Add a photo or video as proof for today.")).toBeInTheDocument();
  });

  it("offers no proof before the check-in", async () => {
    show({ ...walk, state: "todo", settled: false, proofs: [] });
    expect(await screen.findByRole("heading", { name: "Walk" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Add a photo or video" })).toBeNull();
  });

  it("shows this phone's uploads with their progress; a tap pauses", async () => {
    useUploads.getState().put({
      id: "up1",
      proofId: "p9",
      challengeId: "walk",
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

  it("offers no + once the day has five proofs (failed ones do not count)", async () => {
    const five = ["a", "b", "c", "d", "e"].map((id) => saved(id, "photo", "ready"));
    show({ ...walk, proofs: [...five, saved("f", "photo", "failed")] });

    expect(await screen.findAllByRole("button", { name: "Photo. Tap to open" })).toHaveLength(5);
    expect(screen.queryByRole("button", { name: "Add a photo or video" })).toBeNull();
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

function CheckInTab() {
  const { action } = useCheckInAction(true);
  return <TabBar label="Navigation" tabs={[]} action={action} />;
}

describe("the check-in tab while proofs upload", () => {
  it("shows how far the uploads are and how many", async () => {
    useUploads.getState().put({
      id: "up1",
      proofId: "p9",
      challengeId: "walk",
      kind: "video",
      preview: null,
      state: "uploading",
      progress: 0.5,
      size: 100,
    });
    vi.spyOn(api, "GET").mockImplementation((() => ok(today(walk))) as never);
    renderRoutes([{ path: "/", element: <CheckInTab /> }]);

    expect(
      await screen.findByRole("button", { name: "Check in. Uploading proof, 50% (1)" }),
    ).toBeInTheDocument();
  });
});
