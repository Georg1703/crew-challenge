import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/api";
import { ana, bogdan, crewDetail } from "@/test/fixtures";
import { fail, ok, renderRoutes } from "@/test/render";

import { ChallengeBoard, CrewFeed } from ".";
import type { FeedItem, Proof } from "./api";

const person = (member: typeof ana) => ({
  id: member.id,
  display_name: member.display_name,
  avatar_seed: member.avatar_seed,
});

const photo = (id: string): Proof => ({
  id,
  kind: "photo",
  status: "ready",
  url: `/media/${id}.jpg`,
  hls_url: null,
  thumb_url: `/media/${id}-thumb.jpg`,
  created_at: "2026-11-10T08:00:00Z",
  duration: null,
});

const walked: FeedItem = {
  id: "c1",
  member: person(bogdan),
  challenge: { id: "walk", title: "Walk", icon: "walk", measure: "check", unit: "" },
  day: "2026-11-10",
  status: "done",
  total: null,
  activity_at: "2026-11-10T08:30:00Z",
  proofs: ["a", "b", "c", "d", "e"].map(photo),
  streak: 4,
  day_index: 10,
  day_count: 30,
  week: [],
  last_amount: null,
  target: null,
  milestone: null,
  day_summary: { check_ins: 3, proofs: 5, crew_done: false },
  reactions: { groups: [], mine: null },
};
const read: FeedItem = {
  id: "c2",
  member: person(ana),
  challenge: { id: "read", title: "Read", icon: "book", measure: "quantity", unit: "pages" },
  day: "2026-11-09",
  status: "in_progress",
  total: 12,
  activity_at: "2026-11-09T19:40:00Z",
  proofs: [],
  streak: 0,
  day_index: 9,
  day_count: 30,
  week: [],
  last_amount: 4,
  target: 20,
  milestone: null,
  day_summary: { check_ins: 1, proofs: 0, crew_done: false },
  reactions: { groups: [], mine: null },
};

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

const members = [crewDetail.members[0], crewDetail.members[1]].filter((m) => m !== undefined);

function showFeed(results: FeedItem[]) {
  vi.spyOn(api, "GET").mockImplementation((() => ok({ results, next: null })) as never);
  renderRoutes([{ path: "/", element: <CrewFeed timeZone="Europe/Chisinau" members={members} /> }]);
}

const plainWalk = (id: string, member: typeof ana, at: string): FeedItem => ({
  ...walked,
  id,
  member: person(member),
  activity_at: at,
  proofs: [],
});

describe("the crew journal", () => {
  it("shows each day under its divider, with cards that say who did what", async () => {
    showFeed([walked, read]);

    expect(await screen.findByText("Bogdan checked in")).toBeInTheDocument();
    expect(screen.getAllByRole("heading", { level: 2 })).toHaveLength(2);
    expect(screen.getByText("3 check-ins, 5 proofs")).toBeInTheDocument();
    expect(screen.getByText("Streak 4")).toBeInTheDocument();
    expect(screen.getByText("day 10 of 30")).toBeInTheDocument();
    expect(screen.getByText("Ana added")).toBeInTheDocument();
    expect(screen.getByText("+4 pages")).toBeInTheDocument();
    expect(screen.getByRole("progressbar", { name: "12 of 20 pages" })).toBeInTheDocument();
  });

  it("shows three proofs with +N, and opens them", async () => {
    showFeed([walked]);

    expect(await screen.findAllByRole("button", { name: "Photo by Bogdan" })).toHaveLength(3);
    await userEvent.click(screen.getByRole("button", { name: "2 more" }));

    const viewer = await screen.findByRole("dialog", { name: "Proofs" });
    expect(within(viewer).getByText("4 / 5")).toBeInTheDocument();
    expect(within(viewer).getByText("Bogdan, Walk")).toBeInTheDocument();
  });

  it("says plain check-ins of one challenge in one card", async () => {
    showFeed([
      plainWalk("w1", bogdan, "2026-11-10T09:00:00Z"),
      plainWalk("w2", ana, "2026-11-10T08:00:00Z"),
    ]);

    expect(await screen.findByText("Bogdan and Ana checked in")).toBeInTheDocument();
    expect(screen.getAllByRole("article")).toHaveLength(1);
  });

  it("gives a streak milestone and the crew's whole day cards of their own", async () => {
    showFeed([
      {
        ...plainWalk("w1", bogdan, "2026-11-10T09:00:00Z"),
        streak: 7,
        milestone: { kind: "streak", n: 7 },
        day_summary: { check_ins: 2, proofs: 0, crew_done: true },
      },
    ]);

    expect(await screen.findByText("Bogdan keeps it up")).toBeInTheDocument();
    expect(screen.getByText("days in a row")).toBeInTheDocument();
    expect(screen.getByText("The whole crew finished the day")).toBeInTheDocument();
  });

  it("shows older days on request", async () => {
    const get = vi
      .spyOn(api, "GET")
      .mockImplementation(((_path: string, options: { params: { query: { cursor?: string } } }) =>
        options.params.query.cursor === "c2"
          ? ok({ results: [read], next: null })
          : ok({ results: [walked], next: "c2" })) as never);
    renderRoutes([
      { path: "/", element: <CrewFeed timeZone="Europe/Chisinau" members={members} /> },
    ]);

    await userEvent.click(await screen.findByRole("button", { name: "Show older" }));

    expect(await screen.findByText("Ana added")).toBeInTheDocument();
    expect(get).toHaveBeenLastCalledWith("/api/v1/feed", { params: { query: { cursor: "c2" } } });
    expect(screen.queryByRole("button", { name: "Show older" })).toBeNull();
  });

  it("says what will appear while the crew has done nothing yet", async () => {
    showFeed([]);

    expect(
      await screen.findByText("Check-ins and proofs from the crew will show here."),
    ).toBeInTheDocument();
  });
});

describe("a day on the board", () => {
  const days = Array.from({ length: 30 }, (_, i) => `2026-11-${String(i + 1).padStart(2, "0")}`);

  function showBoard() {
    const get = vi.spyOn(api, "GET").mockImplementation(((
      path: string,
      options: { params: { path: { day?: string } } },
    ) => {
      if (path === "/api/v1/challenges/{challenge_id}/board") {
        return ok({
          days,
          rows: [
            {
              member: person(bogdan),
              states: days.map((d) => (d < "2026-11-10" ? "done" : "future")),
              streak: 9,
              proof_days: ["2026-11-03"],
            },
          ],
        });
      }
      if (path === "/api/v1/challenges/{challenge_id}/days/{day}") {
        const day = options.params.path.day;
        return ok([
          {
            member: person(bogdan),
            state: "done",
            total: null,
            proofs: day === "2026-11-03" ? [photo("p3")] : [],
          },
        ]);
      }
      return fail(404, { code: "not_found" });
    }) as never);
    vi.useFakeTimers({ toFake: ["Date"], now: new Date("2026-11-10T09:00:00Z") });
    renderRoutes([
      {
        path: "/",
        element: (
          <ChallengeBoard
            challengeId="walk"
            title="Walk"
            startDate="2026-11-01"
            endDate="2026-11-30"
            timeZone="Europe/Chisinau"
            meId={bogdan.id}
            fixedDays
          />
        ),
      },
    ]);
    return get;
  }

  it("marks the days with proof and opens a day for everyone, one day at a time", async () => {
    showBoard();

    expect(
      await screen.findByRole("img", { name: "Bogdan: 9 done, 0 missed, days with proof: 1" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Wednesday, November 11" })).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Tuesday, November 3" }));

    const sheet = await screen.findByRole("dialog", { name: "Tuesday, November 3" });
    expect(await within(sheet).findByRole("button", { name: "Photo by Bogdan" })).toBeVisible();
    await userEvent.click(within(sheet).getByRole("button", { name: "Next day" }));
    expect(
      await screen.findByRole("dialog", { name: "Wednesday, November 4" }),
    ).toBeInTheDocument();
  });

  it("does not open a day that has not come yet", async () => {
    const get = showBoard();
    await screen.findByRole("img", { name: /^Bogdan: / }); // his row, not his avatar

    await userEvent.click(screen.getByRole("button", { name: "Wednesday, November 11" }));

    expect(screen.queryByRole("dialog")).toBeNull();
    expect(get).not.toHaveBeenCalledWith(
      "/api/v1/challenges/{challenge_id}/days/{day}",
      expect.anything(),
    );
  });

  it("opens a proof from the day, and Escape closes only the viewer", async () => {
    showBoard();
    await userEvent.click(await screen.findByRole("button", { name: "Tuesday, November 3" }));
    const sheet = await screen.findByRole("dialog", { name: "Tuesday, November 3" });

    await userEvent.click(await within(sheet).findByRole("button", { name: "Photo by Bogdan" }));
    expect(await screen.findByRole("dialog", { name: "Proofs" })).toBeInTheDocument();
    await userEvent.keyboard("{Escape}");

    expect(screen.getByRole("dialog", { name: "Tuesday, November 3" })).toBeInTheDocument();
  });
});
