import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { api } from "@/api";
import { i18n } from "@/i18n";
import { ana, bogdan, crewDetail, meAs } from "@/test/fixtures";
import { fail, ok, renderRoutes } from "@/test/render";

import { ChallengeRoute, ChallengesRoute, ProposeRoute, ProposalsRow } from ".";
import type { Window } from "@/features/checkins";

import type { Challenge, Pool } from "./api";
import { describeRule } from "./describe";
import { startOptions } from "./periods";

const person = (member: typeof ana) => ({
  id: member.id,
  display_name: member.display_name,
  avatar_seed: member.avatar_seed,
});

const pushUps: Challenge = {
  id: "c1",
  title: "50 push-ups",
  rules: "",
  icon: "dumbbell",
  measure: "quantity",
  unit: "push-ups",
  window: "day",
  on_days: [],
  need_kind: "count",
  need_value: 1,
  day_min: 50,
  proof_kind: "video",
  proof_required: true,
  state: "proposed",
  phase: null,
  period_kind: "month",
  period_length: 1,
  period_start: null,
  start_date: null,
  end_date: null,
  chosen_by: null,
  chosen_at: null,
  created_by: person(bogdan),
  created_at: "2026-10-02T09:00:00Z",
  revision: 1,
  vote_count: 1,
  voters: [person(bogdan)],
  my_vote: false,
  mine: false,
  participants: [
    { member: person(ana), left_on: null },
    { member: person(bogdan), left_on: null },
  ],
  taking_part: true,
};

const reading: Challenge = { ...pushUps, id: "c2", title: "Read", vote_count: 3, voters: [] };

const pool: Pool = { proposals: [pushUps], size: 1, limit: 50 };

const scheduled = (overrides: Partial<Challenge> = {}): Challenge => ({
  ...pushUps,
  state: "chosen",
  phase: "upcoming",
  period_kind: "month",
  period_start: "2026-11-01",
  start_date: "2026-11-01",
  end_date: "2026-11-30",
  chosen_by: person(ana),
  chosen_at: "2026-10-05T09:00:00Z",
  ...overrides,
});

const detail = (overrides: Partial<Challenge> = {}): Challenge => ({
  ...pushUps,
  ...overrides,
});

type Value<T> = T | (() => T);
const value = <T,>(v: Value<T>) => (typeof v === "function" ? (v as () => T)() : v);

/** Answers every GET the challenge screens make; pass functions for data a test changes. */
function mockGets(
  member = ana,
  {
    proposals = pool as Value<Pool>,
    chosen = [] as Value<Challenge[]>,
    one = detail() as Value<Challenge>,
    windows = (() => []) as (query: { start?: string; until?: string }) => Window[],
  } = {},
) {
  vi.spyOn(api, "GET").mockImplementation(((
    path: string,
    init?: { params?: { query?: { start?: string; until?: string } } },
  ) => {
    if (path === "/api/v1/me") return ok(meAs(member));
    if (path === "/api/v1/crew") return ok(crewDetail);
    if (path === "/api/v1/proposals") return ok(value(proposals));
    if (path === "/api/v1/challenges") return ok(value(chosen));
    if (path === "/api/v1/challenges/{challenge_id}") return ok(value(one));
    if (path === "/api/v1/challenges/{challenge_id}/windows") {
      return ok(windows(init?.params?.query ?? {}));
    }
    return fail(404, { code: "not_found" });
  }) as never);
}

const routes = [
  { path: "/challenges", element: <ChallengesRoute /> },
  { path: "/challenges/new", element: <ProposeRoute /> },
  { path: "/challenges/:id", element: <ChallengeRoute /> },
];

describe("start options", () => {
  it("offers the rest of this month and the next three", () => {
    expect(startOptions("month", 1, "2026-10-05")).toEqual([
      { periodStart: "2026-10-01", startsOn: "2026-10-06", endsOn: "2026-10-31" },
      { periodStart: "2026-11-01", startsOn: "2026-11-01", endsOn: "2026-11-30" },
      { periodStart: "2026-12-01", startsOn: "2026-12-01", endsOn: "2026-12-31" },
      { periodStart: "2027-01-01", startsOn: "2027-01-01", endsOn: "2027-01-31" },
    ]);
  });

  it("leaves out this month on its last day, unless the challenge runs longer", () => {
    expect(startOptions("month", 1, "2026-10-31").map((o) => o.periodStart)).toEqual([
      "2026-11-01",
      "2026-12-01",
      "2027-01-01",
    ]);
    expect(startOptions("month", 2, "2026-10-31")[0]).toEqual({
      periodStart: "2026-10-01",
      startsOn: "2026-11-01",
      endsOn: "2026-11-30",
    });
  });

  it("offers this week from tomorrow and the next eight Mondays; days have a date field", () => {
    const weeks = startOptions("week", 4, "2026-11-04"); // a Wednesday
    expect(weeks[0]).toEqual({
      periodStart: "2026-11-02",
      startsOn: "2026-11-05",
      endsOn: "2026-11-29",
    });
    expect(weeks.slice(1).map((o) => o.periodStart)).toEqual([
      "2026-11-09",
      "2026-11-16",
      "2026-11-23",
      "2026-11-30",
      "2026-12-07",
      "2026-12-14",
      "2026-12-21",
      "2026-12-28",
    ]);
    expect(startOptions("day", 21, "2026-11-04")).toEqual([]);
  });
});

describe("challenges list", () => {
  it("shows the pool with who proposed, the votes and how full it is", async () => {
    mockGets(bogdan);
    renderRoutes(routes, { at: "/challenges" });

    expect(await screen.findByRole("heading", { name: "Proposals" })).toBeInTheDocument();
    expect(screen.getByText("1 of 50")).toBeInTheDocument();
    expect(screen.getByText("50 push-ups")).toBeInTheDocument();
    expect(screen.getByText(/Proposed by Bogdan/)).toBeInTheDocument();
    expect(screen.getByText("Votes: 1")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Choose" })).not.toBeInTheDocument();
  });

  it("says when the pool is empty", async () => {
    mockGets(bogdan, { proposals: { proposals: [], size: 0, limit: 50 } });
    renderRoutes(routes, { at: "/challenges" });

    expect(
      await screen.findByText("No proposals yet. Propose what the crew could do next."),
    ).toBeInTheDocument();
  });

  it("stops new proposals when the pool is full", async () => {
    mockGets(bogdan, { proposals: { ...pool, size: 1, limit: 1 } });
    renderRoutes(routes, { at: "/challenges" });

    expect(await screen.findByText(/The list is full \(1 proposals\)/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Propose a challenge" })).toBeDisabled();
  });

  it("puts the propose button under the running challenges", async () => {
    mockGets(bogdan, {
      chosen: [scheduled({ id: "c5", title: "Walk", phase: "active" }), scheduled()],
    });
    renderRoutes(routes, { at: "/challenges" });

    const active = await screen.findByRole("heading", { name: "Active now" });
    const button = screen.getByRole("button", { name: "Propose a challenge" });
    const upcoming = screen.getByRole("heading", { name: "Coming up" });
    expect(active.compareDocumentPosition(button) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(
      button.compareDocumentPosition(upcoming) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
  });

  it("groups upcoming challenges by month", async () => {
    mockGets(bogdan, {
      chosen: [
        scheduled(),
        scheduled({ id: "c3", title: "Read" }),
        scheduled({
          id: "c4",
          title: "Swim",
          period_start: "2026-12-01",
          start_date: "2026-12-01",
          end_date: "2026-12-31",
        }),
      ],
    });
    renderRoutes(routes, { at: "/challenges" });

    expect(await screen.findByRole("heading", { name: "November 2026" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "December 2026" })).toBeInTheDocument();
    expect(screen.getByRole("list", { name: "November 2026" }).children).toHaveLength(2);
  });

  it("votes for a proposal and shows the vote at once", async () => {
    let current = pool;
    mockGets(bogdan, { proposals: () => current });
    const put = vi.spyOn(api, "PUT").mockImplementation((() => {
      const voted = { ...pushUps, my_vote: true, vote_count: 2 };
      current = { ...pool, proposals: [voted] };
      return ok(voted);
    }) as never);
    renderRoutes(routes, { at: "/challenges" });

    await userEvent.click(await screen.findByRole("button", { name: "Vote" }));

    expect(await screen.findByRole("button", { name: "Voted" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByText("Votes: 2")).toBeInTheDocument();
    expect(put).toHaveBeenCalledWith("/api/v1/challenges/{challenge_id}/vote", {
      params: { path: { challenge_id: "c1" } },
    });
  });

  it("lets an admin sort by votes", async () => {
    mockGets(ana, { proposals: { proposals: [pushUps, reading], size: 2, limit: 50 } });
    renderRoutes(routes, { at: "/challenges" });

    await screen.findByText("50 push-ups");
    const titles = () => screen.getAllByRole("link").map((link) => link.textContent);
    expect(titles()[0]).toContain("50 push-ups");
    await userEvent.click(screen.getByRole("radio", { name: "Most votes" }));
    expect(titles()[0]).toContain("Read");
  });

  it("lets an admin pick a Monday for a proposal that runs in weeks", async () => {
    vi.useFakeTimers({ toFake: ["Date"], now: new Date("2026-11-04T09:00:00Z") }); // a Wednesday
    const weekly = detail({ period_kind: "week", period_length: 4 });
    mockGets(ana, { proposals: { ...pool, proposals: [weekly] }, one: weekly });
    const put = vi.spyOn(api, "PUT").mockImplementation((() => ok(scheduled())) as never);
    renderRoutes(routes, { at: "/challenges" });

    await userEvent.click(await screen.findByRole("button", { name: "Choose" }));
    const sheet = await screen.findByRole("dialog");
    expect(
      within(sheet).getByRole("radio", { name: /^Week of November 2(?!\d)/ }),
    ).toBeInTheDocument();
    expect(within(sheet).getByText("From tomorrow, November 5, to November 29")).toBeVisible();
    expect(within(sheet).getByRole("radio", { name: /Week of November 9/ })).toBeChecked();
    await userEvent.click(within(sheet).getByRole("button", { name: "Choose from November 9" }));

    expect(put).toHaveBeenCalledWith("/api/v1/challenges/{challenge_id}/schedule", {
      params: { path: { challenge_id: "c1" } },
      body: { period_start: "2026-11-09" },
    });
    vi.useRealTimers();
  });

  it("lets an admin pick the first day of a proposal that runs a number of days", async () => {
    vi.useFakeTimers({ toFake: ["Date"], now: new Date("2026-11-04T09:00:00Z") });
    const days = detail({ period_kind: "day", period_length: 21 });
    mockGets(ana, { proposals: { ...pool, proposals: [days] }, one: days });
    const put = vi.spyOn(api, "PUT").mockImplementation((() => ok(scheduled())) as never);
    renderRoutes(routes, { at: "/challenges" });

    await userEvent.click(await screen.findByRole("button", { name: "Choose" }));
    const sheet = await screen.findByRole("dialog");
    const first = within(sheet).getByLabelText("First day");
    expect(first).toHaveValue("2026-11-05"); // tomorrow
    expect(within(sheet).getByText("Until November 25")).toBeVisible();
    fireEvent.change(first, { target: { value: "2026-11-10" } });
    expect(within(sheet).getByText("Until November 30")).toBeVisible();
    await userEvent.click(within(sheet).getByRole("button", { name: "Choose from November 10" }));

    expect(put).toHaveBeenCalledWith("/api/v1/challenges/{challenge_id}/schedule", {
      params: { path: { challenge_id: "c1" } },
      body: { period_start: "2026-11-10" },
    });
    vi.useRealTimers();
  });

  it("says when the chosen start cuts the first week short", async () => {
    vi.useFakeTimers({ toFake: ["Date"], now: new Date("2026-11-04T09:00:00Z") }); // a Wednesday
    const swim = detail({ period_kind: "day", period_length: 10, window: "week", need_value: 3 });
    const week = (first: string, last: string, need: number): Window => ({
      first,
      last,
      need,
      full_need: 3,
      done: null,
      state: null,
    });
    mockGets(ana, {
      proposals: { ...pool, proposals: [swim] },
      one: swim,
      windows: ({ start }) =>
        start === "2026-11-05"
          ? [week("2026-11-05", "2026-11-08", 2), week("2026-11-09", "2026-11-14", 3)]
          : [week("2026-11-09", "2026-11-15", 3), week("2026-11-16", "2026-11-18", 1)],
    });
    renderRoutes(routes, { at: "/challenges" });

    await userEvent.click(await screen.findByRole("button", { name: "Choose" }));
    const sheet = await screen.findByRole("dialog");
    expect(await within(sheet).findByText("Short week: Thu – Sun, 2 instead of 3")).toBeVisible(); // tomorrow is a Thursday
    fireEvent.change(within(sheet).getByLabelText("First day"), {
      target: { value: "2026-11-09" },
    });
    expect(await within(sheet).findByText("Short week: Mon – Wed, 1 instead of 3")).toBeVisible();
    expect(within(sheet).queryByText(/Thu – Sun/)).not.toBeInTheDocument();
    vi.useRealTimers();
  });

  it("lets an admin choose the month for a proposal", async () => {
    vi.useFakeTimers({ toFake: ["Date"], now: new Date("2026-10-05T09:00:00Z") });
    mockGets(ana);
    const put = vi
      .spyOn(api, "PUT")
      .mockImplementation((() => ok(detail({ ...scheduled() }))) as never);
    renderRoutes(routes, { at: "/challenges" });

    await userEvent.click(await screen.findByRole("button", { name: "Choose" }));
    const sheet = await screen.findByRole("dialog");
    expect(within(sheet).getByText("When does “50 push-ups” run?")).toBeVisible();
    expect(within(sheet).getByRole("radio", { name: /October 2026/ })).toBeInTheDocument();
    expect(within(sheet).getByRole("radio", { name: /November 2026/ })).toBeChecked();
    await userEvent.click(within(sheet).getByRole("radio", { name: /December 2026/ }));
    await userEvent.click(within(sheet).getByRole("button", { name: "Choose for December" }));

    expect(await screen.findByText("Scheduled for December")).toBeInTheDocument();
    expect(put).toHaveBeenCalledWith("/api/v1/challenges/{challenge_id}/schedule", {
      params: { path: { challenge_id: "c1" } },
      body: { period_start: "2026-12-01" },
    });
    vi.useRealTimers();
  });
});

describe("proposing", () => {
  it("asks for a name before moving on", async () => {
    mockGets(bogdan);
    renderRoutes(routes, { at: "/challenges/new" });

    await userEvent.click(await screen.findByRole("button", { name: "Continue" }));

    expect(await screen.findByText("Give the challenge a name.")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "What do you propose?" })).toBeInTheDocument();
  });

  it("offers a rule per month once the challenge runs 2 months or more", async () => {
    mockGets(bogdan);
    const post = vi.spyOn(api, "POST").mockImplementation((() => ok(detail(), 201)) as never);
    renderRoutes(routes, { at: "/challenges/new" });

    await userEvent.type(await screen.findByLabelText("Name of the challenge"), "Cook");
    for (const heading of ["Who takes part?", "What do you record?", "How often?"]) {
      await userEvent.click(screen.getByRole("button", { name: "Continue" }));
      await screen.findByRole("heading", { name: heading });
    }
    expect(screen.queryByRole("radio", { name: /A few times a month/ })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "More" })); // 2 months
    await userEvent.click(screen.getByRole("radio", { name: /A few times a month/ }));
    for (const heading of ["What proof?", "Check it"]) {
      await userEvent.click(screen.getByRole("button", { name: "Continue" }));
      await screen.findByRole("heading", { name: heading });
    }
    expect(screen.getByText("3 times a month")).toBeInTheDocument();
    expect(screen.getByText("2 months")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Publish the proposal" }));

    await waitFor(() =>
      expect(post).toHaveBeenCalledWith(
        "/api/v1/challenges",
        expect.objectContaining({
          body: expect.objectContaining({
            window: "month",
            need_kind: "count",
            need_value: "3",
            period_kind: "month",
            period_length: 2,
          }),
        }),
      ),
    );
  });

  it("walks through the steps and publishes the proposal", async () => {
    mockGets(bogdan);
    const post = vi.spyOn(api, "POST").mockImplementation((() => ok(detail(), 201)) as never);
    const { router } = renderRoutes(routes, { at: "/challenges/new" });

    await userEvent.type(await screen.findByLabelText("Name of the challenge"), "Read");
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));

    await screen.findByRole("heading", { name: "Who takes part?" });
    expect(await screen.findByText("The whole crew takes part.")).toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: /Bogdan/ })).toBeDisabled(); // the creator
    await userEvent.click(screen.getByRole("checkbox", { name: /Ana/ }));
    expect(screen.getByText("1 of 2 take part. Only they see the challenge.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));

    await screen.findByRole("heading", { name: "What do you record?" });
    await userEvent.click(screen.getByRole("radio", { name: /A number/ }));
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));
    expect(await screen.findByText("Write the unit, for example km.")).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("Unit"), "pages");
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));

    await screen.findByRole("heading", { name: "How often?" });
    await userEvent.click(screen.getByRole("radio", { name: "Weeks" }));
    for (let n = 0; n < 3; n += 1)
      await userEvent.click(screen.getByRole("button", { name: "More" }));
    expect(screen.getByLabelText("Each check-in at least (pages)")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("radio", { name: /A total each week/ }));
    expect(screen.queryByLabelText("Each check-in at least (pages)")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));
    expect(await screen.findByText("Write a number above zero.")).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("Total (pages)"), "50");
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));

    await screen.findByRole("heading", { name: "What proof?" });
    await userEvent.click(screen.getByRole("radio", { name: /Quick, works for almost anything/ }));
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));

    await screen.findByRole("heading", { name: "Check it" });
    expect(screen.getByText("50 pages a week")).toBeInTheDocument();
    expect(screen.getByText("4 weeks")).toBeInTheDocument();
    expect(screen.getByText("Bogdan")).toBeInTheDocument(); // who takes part
    await userEvent.click(screen.getByRole("button", { name: "Publish the proposal" }));

    await waitFor(() => expect(router.state.location.pathname).toBe("/challenges/c1"));
    expect(post).toHaveBeenCalledWith("/api/v1/challenges", {
      body: {
        title: "Read",
        rules: "",
        icon: "star",
        measure: "quantity",
        unit: "pages",
        window: "week",
        on_days: [],
        need_kind: "amount",
        need_value: "50",
        day_min: null,
        period_kind: "week",
        period_length: 4,
        proof_kind: "photo",
        proof_required: false,
        participant_ids: [bogdan.id],
      },
    });
  });

  it("explains a full pool", async () => {
    mockGets(bogdan);
    vi.spyOn(api, "POST").mockImplementation((() => fail(409, { code: "pool_full" })) as never);
    renderRoutes(routes, { at: "/challenges/new" });

    await userEvent.type(await screen.findByLabelText("Name of the challenge"), "Read");
    for (let step = 0; step < 5; step += 1) {
      await userEvent.click(screen.getByRole("button", { name: "Continue" }));
    }
    await userEvent.click(await screen.findByRole("button", { name: "Publish the proposal" }));

    expect(await screen.findByText(/The list of proposals is full/)).toBeInTheDocument();
  });
});

describe("one challenge", () => {
  it("shows who takes part and lets the creator change it", async () => {
    let one = detail({ mine: true });
    mockGets(bogdan, { one: () => one });
    const put = vi.spyOn(api, "PUT").mockImplementation((() => {
      one = detail({ mine: true, participants: [{ member: person(bogdan), left_on: null }] });
      return ok(one);
    }) as never);
    renderRoutes(routes, { at: "/challenges/c1" });

    const list = await screen.findByRole("list", { name: "Who takes part" });
    expect(within(list).getAllByRole("listitem")).toHaveLength(2);
    await userEvent.click(await screen.findByRole("button", { name: "Change who takes part" }));
    const sheet = await screen.findByRole("dialog");
    await userEvent.click(await within(sheet).findByRole("checkbox", { name: /Ana/ }));
    await userEvent.click(within(sheet).getByRole("button", { name: "Save" }));

    expect(await screen.findByText("Participants saved")).toBeInTheDocument();
    expect(put).toHaveBeenCalledWith("/api/v1/challenges/{challenge_id}/participants", {
      params: { path: { challenge_id: "c1" } },
      body: { participant_ids: [bogdan.id] },
    });
    await waitFor(() =>
      expect(
        within(screen.getByRole("list", { name: "Who takes part" })).getAllByRole("listitem"),
      ).toHaveLength(1),
    );
  });

  it("shows an admin who does not take part the proposal without a vote", async () => {
    mockGets(ana, {
      one: detail({
        participants: [{ member: person(bogdan), left_on: null }],
        taking_part: false,
      }),
    });
    renderRoutes(routes, { at: "/challenges/c1" });

    expect(
      await screen.findByText("You see it because you are an admin; you don't take part."),
    ).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "Choose when" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Vote" })).not.toBeInTheDocument();
  });

  it("lets the creator vote, edit or withdraw a proposal", async () => {
    mockGets(bogdan, { one: detail({ mine: true }) });
    renderRoutes(routes, { at: "/challenges/c1" });

    expect(await screen.findByRole("heading", { name: "50 push-ups" })).toBeInTheDocument();
    expect(screen.getByText("At least 50 push-ups each check-in")).toBeInTheDocument();
    expect(screen.getByText("Video, required")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Vote" })).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "Edit the proposal" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Withdraw the proposal" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Choose when" })).not.toBeInTheDocument();
  });

  it("lets an admin move a scheduled challenge or put it back in the pool", async () => {
    const chosen = detail({ ...scheduled(), taking_part: true });
    let one = chosen;
    mockGets(ana, { one: () => one });
    const del = vi.spyOn(api, "DELETE").mockImplementation((() => {
      one = detail();
      return ok(one);
    }) as never);
    renderRoutes(routes, { at: "/challenges/c1" });

    expect(await screen.findByText("For November 2026")).toBeInTheDocument();
    expect(screen.getByText(/Chosen by Ana/)).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "Move it" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Back to proposals" }));

    expect(await screen.findByText("Back in the proposals")).toBeInTheDocument();
    expect(del).toHaveBeenCalledWith("/api/v1/challenges/{challenge_id}/schedule", {
      params: { path: { challenge_id: "c1" } },
    });
    expect(await screen.findByRole("button", { name: "Vote" })).toBeInTheDocument();
  });

  it("shows a running challenge's month and checks in from it", async () => {
    vi.useFakeTimers({ toFake: ["Date"], now: new Date("2026-11-10T09:00:00Z") });
    const running = detail({
      ...scheduled(),
      phase: "active",
      measure: "check",
      taking_part: true,
      participants: [{ member: person(bogdan), left_on: null }],
    });
    const days = Array.from({ length: 30 }, (_, i) => `2026-11-${String(i + 1).padStart(2, "0")}`);
    const todayCard = {
      id: "c1",
      title: "50 push-ups",
      icon: "dumbbell",
      measure: "check",
      unit: "",
      window: "day",
      need_kind: "count",
      need_value: 1,
      day_min: null,
      proof_kind: "none",
      proof_required: false,
      end_date: "2026-11-30",
      state: "todo",
      total: null,
      streak: 9,
      week: [],
      current: null,
      settled: false,
    };
    vi.spyOn(api, "GET").mockImplementation(((path: string) => {
      if (path === "/api/v1/me") return ok(meAs(bogdan));
      if (path === "/api/v1/challenges/{challenge_id}") return ok(running);
      if (path === "/api/v1/challenges/{challenge_id}/board") {
        return ok({
          days,
          rows: [
            {
              member: person(bogdan),
              states: days.map((_, i) => (i < 9 ? "done" : i === 9 ? "todo" : "future")),
              streak: 9,
              proof_days: [],
            },
          ],
        });
      }
      if (path === "/api/v1/today") {
        return ok({
          day: "2026-11-10",
          deadline: "2026-11-10T22:00:00Z",
          challenges: [todayCard],
          crew: [],
        });
      }
      return fail(404, { code: "not_found" });
    }) as never);
    renderRoutes(routes, { at: "/challenges/c1" });

    expect(await screen.findByText("Day 10 of 30")).toBeInTheDocument();
    expect(screen.getByRole("list", { name: "What the challenge asks" })).toHaveTextContent(
      "Every day",
    );
    expect(
      await screen.findByRole("img", { name: "Bogdan: 9 done, 0 missed" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("list", { name: "Taking part" })).not.toBeInTheDocument();
    expect(screen.queryByText(/Votes/)).not.toBeInTheDocument();

    await userEvent.click(await screen.findByRole("button", { name: "Check in today" }));
    const sheet = await screen.findByRole("dialog");
    expect(within(sheet).getByRole("heading", { name: "50 push-ups" })).toBeInTheDocument();
    vi.useRealTimers();
  });

  it("lists a running challenge's weeks and what leaving today makes of this one", async () => {
    vi.useFakeTimers({ toFake: ["Date"], now: new Date("2026-11-10T09:00:00Z") }); // a Tuesday
    const swim = detail({
      ...scheduled({ period_kind: "day", period_length: 10 }),
      period_start: "2026-11-05",
      start_date: "2026-11-05",
      end_date: "2026-11-14",
      phase: "active",
      measure: "check",
      window: "week",
      need_value: 3,
      taking_part: true,
      participants: [{ member: person(bogdan), left_on: null }],
    });
    const first: Window = {
      first: "2026-11-05",
      last: "2026-11-08",
      need: 2,
      full_need: 3,
      done: 2,
      state: "met",
    };
    mockGets(bogdan, {
      one: swim,
      windows: ({ until }) =>
        until
          ? [first, { ...first, first: "2026-11-09", last: "2026-11-10", need: 1, done: 1 }]
          : [
              first,
              {
                ...first,
                first: "2026-11-09",
                last: "2026-11-14",
                need: 3,
                done: 1,
                state: "open",
              },
            ],
    });
    renderRoutes(routes, { at: "/challenges/c1" });

    const weeks = await screen.findByRole("list", { name: "Week by week" });
    expect(weeks).toHaveTextContent("November 5 – November 8");
    expect(weeks).toHaveTextContent("2 of 2 (instead of 3)");
    expect(within(weeks).getByText("Done")).toBeInTheDocument();
    expect(weeks).toHaveTextContent("1 of 3");
    expect(within(weeks).getByText("Now")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Leave the challenge" }));
    const sheet = await screen.findByRole("dialog", { name: "Leave the challenge?" });
    expect(
      await within(sheet).findByText(
        "Your last week would be Mon – Tue and ask for 1 instead of 3.",
      ),
    ).toBeInTheDocument();
    vi.useRealTimers();
  });

  it("lets a member opt out of a scheduled challenge before it starts, after confirming", async () => {
    mockGets(bogdan, {
      one: detail({
        ...scheduled(),
        taking_part: true,
        participants: [{ member: person(bogdan), left_on: null }],
      }),
    });
    const del = vi.spyOn(api, "DELETE").mockImplementation((() => ok(undefined, 204)) as never);
    renderRoutes(routes, { at: "/challenges/c1" });

    await userEvent.click(await screen.findByRole("button", { name: "I'm not taking part" }));
    const sheet = await screen.findByRole("dialog", { name: "Not taking part?" });
    expect(del).not.toHaveBeenCalled();
    await userEvent.click(within(sheet).getByRole("button", { name: "I'm not taking part" }));

    expect(await screen.findByText("You're no longer taking part")).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Challenges" })).toBeInTheDocument();
    expect(del).toHaveBeenCalledWith("/api/v1/challenges/{challenge_id}/participation", {
      params: { path: { challenge_id: "c1" } },
    });
    expect(screen.queryByRole("button", { name: "I'm taking part" })).not.toBeInTheDocument();
  });
});

describe("proposals row", () => {
  const row = (
    member: typeof ana,
    now: string,
    { chosen = [] as Challenge[], proposals = pool } = {},
  ) => {
    mockGets(member, { chosen, proposals });
    renderRoutes([
      {
        path: "/",
        element: (
          <ProposalsRow
            isAdmin={member.role === "admin"}
            timeZone="Europe/Chisinau"
            now={new Date(now)}
          />
        ),
      },
    ]);
  };

  it("says how many proposals wait for your vote, as a link to them", async () => {
    row(bogdan, "2026-10-26T09:00:00Z");
    const link = await screen.findByRole("link", { name: /1 proposal waits for your vote/ });
    expect(link).toHaveAttribute("href", "/challenges");
  });

  it("counts the list once you voted for everything", async () => {
    row(bogdan, "2026-10-26T09:00:00Z", {
      proposals: { ...pool, proposals: [{ ...pushUps, my_vote: true }] },
    });
    expect(await screen.findByRole("link", { name: /1 proposal in the list/ })).toBeInTheDocument();
  });

  it("is not there while the pool is empty", async () => {
    row(bogdan, "2026-10-26T09:00:00Z", { proposals: { ...pool, proposals: [], size: 0 } });
    await waitFor(() => expect(api.GET).toHaveBeenCalledWith("/api/v1/proposals"));
    expect(screen.queryByRole("link")).toBeNull();
  });

  it("reminds admins from the 25th when next month has no challenge", async () => {
    row(ana, "2026-10-26T09:00:00Z");
    expect(
      await screen.findByRole("link", { name: /No challenge for November yet/ }),
    ).toBeInTheDocument();
  });

  it("does not remind admins when next month has a challenge", async () => {
    row(ana, "2026-10-26T09:00:00Z", { chosen: [scheduled()] });
    expect(await screen.findByRole("link", { name: /1 proposal waits/ })).toBeInTheDocument();
    expect(screen.queryByText(/No challenge for November/)).toBeNull();
  });
});

describe("a challenge's rule as a sentence", () => {
  it("names counts, chosen days and totals", () => {
    const say = (rule: Partial<Parameters<typeof describeRule>[1]>) =>
      describeRule(
        i18n.t,
        {
          ...{ window: "day", on_days: [], need_kind: "count", need_value: 1, unit: "km" },
          ...{ period_kind: "month", period_length: 1 },
          ...rule,
        },
        "en",
      );
    expect(say({})).toBe("Every day");
    expect(say({ on_days: [0, 2, 4] })).toBe("On Mon, Wed, Fri");
    expect(say({ window: "week", need_value: 1 })).toBe("Once a week");
    expect(say({ window: "week", need_value: 3 })).toBe("3 times a week");
    expect(say({ window: "period", need_value: 1 })).toBe("Once, by the end");
    expect(say({ window: "period", need_value: "8" })).toBe("8 times in the month");
    expect(say({ window: "period", need_value: 8, period_kind: "week", period_length: 4 })).toBe(
      "8 times in 4 weeks",
    );
    expect(say({ window: "period", need_value: 8, period_kind: "day", period_length: 21 })).toBe(
      "8 times in 21 days",
    );
    expect(say({ window: "week", need_kind: "amount", need_value: "12.5" })).toBe("12.5 km a week");
    expect(say({ window: "period", need_kind: "amount", need_value: 1200 })).toBe(
      "1,200 km in the month",
    );
    expect(say({ window: "period", need_kind: "amount", need_value: 300, period_length: 3 })).toBe(
      "300 km in 3 months",
    );
    expect(say({ window: "month", need_value: 1, period_length: 3 })).toBe("Once a month");
    expect(say({ window: "month", need_value: 4, period_length: 3 })).toBe("4 times a month");
    expect(say({ window: "month", need_kind: "amount", need_value: 100, period_length: 3 })).toBe(
      "100 km a month",
    );
  });
});
