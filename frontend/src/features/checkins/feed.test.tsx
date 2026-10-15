import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/api";
import { ana, bogdan, crewDetail } from "@/test/fixtures";
import { fail, ok, renderRoutes } from "@/test/render";

import { ChallengeBoard, CrewFeed } from ".";
import type { Proof } from "@/features/proofs";

import type { JournalEntry } from "./api";

type Facts = NonNullable<JournalEntry["check_in"]>;

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
  phone_thumb_url: null,
  created_at: "2026-11-10T08:00:00Z",
  duration: null,
  posted: true,
});

const WALK = { id: "walk", title: "Walk", icon: "walk", measure: "check", unit: "" } as const;
const READ = {
  id: "read",
  title: "Read",
  icon: "book",
  measure: "quantity",
  unit: "pages",
} as const;
const SWIM = { id: "swim", title: "Swim", icon: "water", measure: "check", unit: "" } as const;
const SHOWER = { position: 3, text: "Cold shower, 2 minutes", proof_required: true };

/** A card as the journal sends it: its kind's facts set, the others null. */
const card = (over: Partial<JournalEntry>): JournalEntry => ({
  id: "e1",
  kind: "check_in",
  at: "2026-11-10T08:30:00Z",
  day: "2026-11-10",
  member: person(bogdan),
  challenge: WALK,
  proofs: [],
  reactions: { groups: [], mine: null },
  comments: { count: 0, member_ids: [], unread: 0 },
  check_in: null,
  failed: null,
  spin: null,
  served: null,
  crew_day: null,
  ...over,
});
const facts = (over: Partial<Facts> = {}): Facts => ({
  action: "check",
  amount: null,
  total: null,
  target: null,
  streak: 4,
  milestone: null,
  proofs: 0,
  ...over,
});

const walked = card({
  id: "c1",
  proofs: ["a", "b", "c", "d", "e"].map(photo),
  check_in: facts({ proofs: 5 }),
});
const read = card({
  id: "c2",
  member: person(ana),
  challenge: READ,
  day: "2026-11-09",
  at: "2026-11-09T19:40:00Z",
  check_in: facts({ action: "amount", amount: 4, total: 12, target: 20, streak: 0 }),
});
const plainWalk = (id: string, member: typeof ana, at: string) =>
  card({ id, member: person(member), at, check_in: facts() });
const drawn = card({
  id: "s1",
  kind: "spin",
  day: "2026-11-09",
  at: "2026-11-09T08:00:00Z",
  challenge: SWIM,
  spin: {
    window_first: "2026-11-02",
    window_last: "2026-11-08",
    need_kind: "count",
    need: 3,
    done: 1,
    punishment: SHOWER,
    serve_by: "2026-11-16",
  },
});

const DAYS = [
  { day: "2026-11-10", check_ins: 3, proofs: 5 },
  { day: "2026-11-09", check_ins: 1, proofs: 0 },
];

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

const members = [crewDetail.members[0], crewDetail.members[1]].filter((m) => m !== undefined);

function showFeed(results: JournalEntry[]) {
  vi.spyOn(api, "GET").mockImplementation((() => ok({ results, days: DAYS, next: null })) as never);
  renderRoutes([{ path: "/", element: <CrewFeed timeZone="Europe/Chisinau" members={members} /> }]);
}

describe("the crew journal", () => {
  it("shows a failed window with what failed and the spins it owes", async () => {
    showFeed([
      card({
        id: "f1",
        kind: "failed",
        day: "2026-11-09",
        at: "2026-11-08T22:01:00Z",
        challenge: SWIM,
        failed: {
          window_first: "2026-11-02",
          window_last: "2026-11-08",
          need_kind: "count",
          need: 3,
          done: 1,
          spins: 2,
        },
      }),
    ]);

    expect(await screen.findByText("Bogdan fell short")).toBeInTheDocument();
    expect(screen.getByText("November 2 – November 8: 1 of 3")).toBeInTheDocument();
    expect(screen.getByText("Owes 2 spins")).toBeInTheDocument();
  });

  it("shows a drawn spin with its punishment and when it is due", async () => {
    showFeed([drawn]);

    expect(await screen.findByText("Bogdan spun the wheel")).toBeInTheDocument();
    expect(screen.getByText("Cold shower, 2 minutes")).toBeInTheDocument();
    expect(screen.queryByText("3")).toBeNull(); // the text only, not its number on the dial
    expect(screen.getByText("Serve by Monday, November 16")).toBeInTheDocument();
    expect(screen.getByText("November 2 – November 8: 1 of 3")).toBeInTheDocument();
  });

  it("shows a served spin as a card of its own, with its photo and no date to serve by", async () => {
    showFeed([
      card({
        id: "s2",
        kind: "served",
        day: "2026-11-11",
        at: "2026-11-11T10:00:00Z",
        challenge: SWIM,
        proofs: [photo("p1")],
        served: { punishment: SHOWER, proofs: 1 },
      }),
      drawn,
    ]);

    expect(await screen.findByText("Bogdan served a punishment")).toBeInTheDocument();
    expect(screen.getByText("Bogdan spun the wheel")).toBeInTheDocument();
    expect(screen.getAllByText("Cold shower, 2 minutes")).toHaveLength(2);
    expect(screen.getAllByText(/^Serve by/)).toHaveLength(1); // the drawn card, as it was
    expect(screen.getByRole("button", { name: "Photo by Bogdan" })).toBeInTheDocument();
  });

  it("shows each day under its divider, with cards that say who did what", async () => {
    showFeed([walked, read]);

    expect(await screen.findByText("Bogdan checked in")).toBeInTheDocument();
    expect(screen.getAllByRole("heading", { level: 2 })).toHaveLength(2);
    expect(screen.getByText("3 check-ins, 5 proofs")).toBeInTheDocument();
    expect(screen.getByText("Streak 4")).toBeInTheDocument();
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

  it("gives every check-in a card of its own, and says files added later", async () => {
    showFeed([
      card({
        id: "f1",
        proofs: [photo("p1"), photo("p2")],
        check_in: facts({ action: "files", proofs: 2 }),
      }),
      plainWalk("w1", bogdan, "2026-11-10T09:00:00Z"),
      plainWalk("w2", ana, "2026-11-10T08:00:00Z"),
    ]);

    expect(await screen.findByText("Bogdan added 2 photos and videos")).toBeInTheDocument();
    expect(screen.getByText("Ana checked in")).toBeInTheDocument();
    expect(screen.getAllByRole("article")).toHaveLength(3);
  });

  it("gives a streak milestone and the crew's whole day cards of their own", async () => {
    showFeed([
      card({
        id: "d1",
        kind: "crew_day",
        member: null,
        challenge: null,
        crew_day: { members: [ana.id, bogdan.id] },
      }),
      card({ id: "w1", check_in: facts({ streak: 7, milestone: 7 }) }),
    ]);

    expect(await screen.findByText("Bogdan keeps it up")).toBeInTheDocument();
    expect(screen.getByText("days in a row")).toBeInTheDocument();
    expect(screen.getByText("The whole crew finished the day")).toBeInTheDocument();
  });

  it("shows older days on request", async () => {
    const get = vi.spyOn(api, "GET").mockImplementation(((
      path: string,
      options: { params: { query: { cursor?: string } } },
    ) =>
      path !== "/api/v1/journal"
        ? ok({}) // who is asking (reactions)
        : options.params.query.cursor === "c2"
          ? ok({ results: [read], days: DAYS, next: null })
          : ok({ results: [walked], days: DAYS, next: "c2" })) as never);
    renderRoutes([
      { path: "/", element: <CrewFeed timeZone="Europe/Chisinau" members={members} /> },
    ]);

    await userEvent.click(await screen.findByRole("button", { name: "Show older" }));

    expect(await screen.findByText("Ana added")).toBeInTheDocument();
    expect(get).toHaveBeenCalledWith("/api/v1/journal", { params: { query: { cursor: "c2" } } });
    expect(screen.queryByRole("button", { name: "Show older" })).toBeNull();
  });

  it("lets the crew react to every card, each its own", async () => {
    showFeed([
      {
        ...walked,
        reactions: { groups: [{ emoji: "\u{1F525}", member_ids: [ana.id] }], mine: null },
      },
      plainWalk("w1", bogdan, "2026-11-10T07:00:00Z"),
      drawn,
    ]);

    expect(await screen.findByRole("button", { name: "\u{1F525}, from Ana" })).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "React" })).toHaveLength(3);
  });

  it("links every card to its comments, marking the ones with new ones", async () => {
    showFeed([
      { ...walked, comments: { count: 3, member_ids: [ana.id], unread: 2 } },
      plainWalk("w1", bogdan, "2026-11-10T07:00:00Z"),
    ]);

    const commented = await screen.findByRole("link", { name: /3 comments, 2 new/ });
    expect(commented).toHaveAttribute("href", `/crew/cards/${walked.id}`);
    expect(screen.getByRole("link", { name: "Comment" })).toBeInTheDocument();
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
