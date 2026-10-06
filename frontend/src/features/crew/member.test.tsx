import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/api";
import type { FeedItem, MemberProgress } from "@/features/checkins";
import { ana, bogdan, crewDetail, meAs } from "@/test/fixtures";
import { fail, ok, renderRoutes } from "@/test/render";

import { CrewRoute, MemberRoute } from ".";
import { freshCounts, markSeen, seenAt } from "./seen";

const person = (m: typeof ana) => ({
  id: m.id,
  display_name: m.display_name,
  avatar_seed: m.avatar_seed,
});

const days = Array.from({ length: 30 }, (_, i) => `2026-11-${String(i + 1).padStart(2, "0")}`);
const walk = { id: "walk", title: "Walk", icon: "walk", measure: "check", unit: "" } as const;
const proof = (id: string, at = "2026-11-10T08:00:00Z") => ({
  id,
  kind: "photo" as const,
  status: "ready" as const,
  url: `/media/${id}.jpg`,
  hls_url: null,
  thumb_url: null,
  created_at: at,
  duration: null,
});

const progress: MemberProgress = {
  member: person(bogdan),
  days,
  streak: 4,
  longest_streak: 9,
  month_done: 9,
  month_due: 10,
  challenges: [
    {
      challenge: walk,
      states: days.map((d) => (d < "2026-11-10" ? "done" : "future")),
      proof_days: ["2026-11-03"],
      streak: 4,
      today: "todo",
    },
  ],
  proof_days: [
    { day: "2026-11-09", challenge: walk, proofs: [proof("a"), proof("b")] },
    { day: "2026-11-03", challenge: walk, proofs: [proof("c")] },
  ],
};

const routes = [
  { path: "/crew", element: <CrewRoute /> },
  { path: "/crew/members", element: <p>members screen</p> },
  { path: "/crew/members/:id", element: <MemberRoute /> },
];

function mockGets(member: MemberProgress | null, feed: FeedItem[] = []) {
  vi.spyOn(api, "GET").mockImplementation(((path: string) => {
    if (path === "/api/v1/me") return ok(meAs(ana));
    if (path === "/api/v1/members/{member_id}/progress") {
      return member ? ok(member) : fail(404, { code: "member_not_found" });
    }
    if (path === "/api/v1/today") {
      return ok({ day: "2026-11-10", deadline: "2026-11-10T22:00:00Z", challenges: [], crew: [] });
    }
    if (path === "/api/v1/feed") return ok({ results: feed, next: null });
    if (path === "/api/v1/proposals") return ok({ proposals: [], size: 0, limit: 50 });
    if (path === "/api/v1/challenges") return ok([]);
    return ok(crewDetail);
  }) as never);
}

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
});

describe("a member's page", () => {
  it("shows their streaks, their month per challenge and their proofs by day", async () => {
    mockGets(progress);
    renderRoutes(routes, { at: `/crew/members/${bogdan.id}` });

    expect(await screen.findByRole("heading", { level: 1, name: "Bogdan" })).toBeInTheDocument();
    expect(screen.getByText("90%")).toBeInTheDocument();
    expect(screen.getByText("longest streak")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Walk this month" })).toBeInTheDocument();
    const proofs = screen.getByRole("region", { name: "Proofs" });
    expect(within(proofs).getAllByRole("heading", { level: 2 })).toHaveLength(2);

    await userEvent.click(
      within(proofs).getAllByRole("button", { name: "Photo by Bogdan" })[1] as HTMLElement,
    );
    const viewer = await screen.findByRole("dialog", { name: "Proofs" });
    expect(within(viewer).getByText("2 / 2")).toBeInTheDocument();
  });

  it("marks their proofs seen on this device", async () => {
    mockGets(progress);
    renderRoutes(routes, { at: `/crew/members/${bogdan.id}` });
    await screen.findByRole("heading", { level: 1, name: "Bogdan" });
    expect(seenAt(crewDetail.id, bogdan.id)).not.toBeNull();
  });

  it("says when the member is not in your crew", async () => {
    mockGets(null);
    renderRoutes(routes, { at: "/crew/members/someone" });
    expect(await screen.findByText("This member is not in your crew.")).toBeInTheDocument();
  });
});

describe("echipa", () => {
  it("opens members and invites from the button next to the title", async () => {
    mockGets(progress);
    renderRoutes(routes, { at: "/crew" });
    await userEvent.click(await screen.findByRole("button", { name: "Members and invites" }));
    expect(await screen.findByText("members screen")).toBeInTheDocument();
  });
});

describe("new proofs", () => {
  const item = (memberProofs: ReturnType<typeof proof>[], who = bogdan) =>
    ({ member: person(who), proofs: memberProofs }) as unknown as FeedItem;

  it("counts proofs after you last looked, never your own, and resets once seen", () => {
    const since = new Date("2026-11-10T00:00:00Z");
    const items = [
      item([proof("a", "2026-11-10T08:00:00Z"), proof("b", "2026-11-09T08:00:00Z")]),
      item([proof("c", "2026-11-10T09:00:00Z")], ana),
    ];
    expect(freshCounts(items, "crew", ana.id, since)).toEqual({ [bogdan.id]: 1 });
    markSeen("crew", bogdan.id, new Date("2026-11-10T08:30:00Z"));
    expect(freshCounts(items, "crew", ana.id, since)).toEqual({});
  });

  it("gives no badge when storage is blocked", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    markSeen("crew", bogdan.id);
    expect(seenAt("crew", bogdan.id)).toBeNull();
  });
});
