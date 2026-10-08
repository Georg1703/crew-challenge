import { screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "@/api";
import { TabBar } from "@/shared/ui";
import { bogdan, meAs } from "@/test/fixtures";
import { fail, ok, renderRoutes } from "@/test/render";

import { TodayCheckIns, useCheckInAction } from ".";
import { useUploads, type Proof } from "@/features/proofs";

import type { Today, TodayChallenge } from "./api";

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
  it("shows the day's proofs and + once checked in", async () => {
    show();
    expect(await screen.findByRole("button", { name: "Photo. Tap to open" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add a photo or video" })).toBeInTheDocument();
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
      subject: "check-in:walk",
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
