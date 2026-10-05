import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/api";
import { HoldButton, TabBar } from "@/shared/ui";
import { ana, bogdan, meAs } from "@/test/fixtures";
import { fail, ok, renderRoutes } from "@/test/render";

import { ChallengeBoard, CheckInSheet, TodayCheckIns, useCheckInAction } from ".";
import type { Today, TodayChallenge } from "./api";

const person = (member: typeof ana) => ({
  id: member.id,
  display_name: member.display_name,
  avatar_seed: member.avatar_seed,
});

const week = (today: TodayChallenge["state"]): TodayChallenge["week"] =>
  [
    "2026-11-09",
    "2026-11-10",
    "2026-11-11",
    "2026-11-12",
    "2026-11-13",
    "2026-11-14",
    "2026-11-15",
  ].map((day, i) => ({ day, state: i === 0 ? "done" : i === 1 ? today : "future" }));

const walk: TodayChallenge = {
  id: "walk",
  title: "Walk",
  icon: "walk",
  measure: "check",
  unit: "",
  frequency: "daily",
  times: null,
  target_scope: "none",
  target_value: null,
  proof_kind: "none",
  proof_required: false,
  end_date: "2026-11-30",
  state: "todo",
  total: null,
  streak: 1,
  week: week("todo"),
  progress: null,
  settled: false,
};

const read: TodayChallenge = {
  ...walk,
  id: "read",
  title: "Read",
  icon: "book",
  measure: "quantity",
  unit: "pages",
  target_scope: "per_check_in",
  target_value: 20,
  state: "partial",
  total: 12,
  streak: 0,
  week: week("partial"),
};

const today = (challenges: TodayChallenge[], deadline = "2026-11-10T22:00:00Z"): Today => ({
  day: "2026-11-10",
  deadline,
  challenges,
  crew: [
    { member: person(ana), done: 2, needed: 2 },
    { member: person(bogdan), done: 0, needed: 2 },
  ],
});

function mockToday(data: Today | (() => Today)) {
  vi.spyOn(api, "GET").mockImplementation(((path: string) => {
    if (path === "/api/v1/me") return ok(meAs(bogdan));
    if (path === "/api/v1/today") return ok(typeof data === "function" ? data() : data);
    return fail(404, { code: "not_found" });
  }) as never);
}

const show = () => renderRoutes([{ path: "/", element: <TodayCheckIns /> }]);

afterEach(() => vi.useRealTimers());

describe("today", () => {
  it("shows the day ring and a card per challenge, not the crew (that is on Echipa)", async () => {
    mockToday(today([walk, read]));
    show();

    expect(await screen.findByRole("img", { name: "0 of 2 done today" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Walk" })).toBeInTheDocument();
    expect(screen.getByText("Streak: 1")).toBeInTheDocument();
    expect(screen.getByText("12 / 20 pages")).toBeInTheDocument();
    expect(screen.getByRole("progressbar", { name: "12 / 20 pages" })).toBeInTheDocument();
    expect(screen.getAllByRole("img", { name: "Monday: done" })).toHaveLength(2);
    expect(screen.queryByRole("img", { name: /^Ana:/ })).not.toBeInTheDocument();
  });

  it("checks in at once and offers undo", async () => {
    let data = today([walk]);
    mockToday(() => data);
    const post = vi.spyOn(api, "POST").mockImplementation((() => {
      const done = {
        ...walk,
        state: "done" as const,
        settled: true,
        streak: 2,
        week: week("done"),
      };
      data = today([done]);
      return ok(done);
    }) as never);
    const del = vi.spyOn(api, "DELETE").mockImplementation((() => ok({ ...walk })) as never);
    show();

    const hold = await screen.findByRole("button", { name: "Hold to check in" });
    hold.focus();
    await userEvent.keyboard("{Enter}"); // keyboard confirms at once

    expect(await screen.findByRole("button", { name: "Done today" })).toBeInTheDocument();
    expect(post).toHaveBeenCalledWith("/api/v1/challenges/{challenge_id}/check-ins", {
      params: { path: { challenge_id: "walk" } },
      body: { day: "2026-11-10", amount: null },
    });
    expect(await screen.findByText("Day done")).toBeInTheDocument();

    await userEvent.click(await screen.findByRole("button", { name: "Undo" }));
    expect(del).toHaveBeenCalledWith("/api/v1/challenges/{challenge_id}/check-ins/{day}/last", {
      params: { path: { challenge_id: "walk", day: "2026-11-10" } },
    });
  });

  it("adds a number and rolls back when the day has closed", async () => {
    mockToday(today([read]));
    let answer: (value: unknown) => void = () => undefined;
    vi.spyOn(api, "POST").mockImplementation(
      (() => new Promise((resolve) => (answer = resolve))) as never,
    );
    show();

    await userEvent.click(await screen.findByRole("button", { name: "+5" }));
    expect(await screen.findByText("17 / 20 pages")).toBeInTheDocument(); // before the answer
    await act(async () => answer(await fail(409, { code: "day_closed" })));
    expect(
      await screen.findByText("That day has ended. You can only check in for today."),
    ).toBeInTheDocument();
    expect(screen.getByText("12 / 20 pages")).toBeInTheDocument();
  });

  it("types another number in a sheet", async () => {
    mockToday(today([read]));
    const post = vi
      .spyOn(api, "POST")
      .mockImplementation((() =>
        ok({ ...read, total: 32, state: "done", settled: true })) as never);
    show();

    await userEvent.click(await screen.findByRole("button", { name: "Other" }));
    const sheet = await screen.findByRole("dialog");
    await userEvent.type(within(sheet).getByLabelText("How many pages"), "0");
    await userEvent.click(within(sheet).getByRole("button", { name: "Add" }));
    expect(within(sheet).getByText("Write a number above zero.")).toBeInTheDocument();
    await userEvent.clear(within(sheet).getByLabelText("How many pages"));
    await userEvent.type(within(sheet).getByLabelText("How many pages"), "20,5");
    await userEvent.click(within(sheet).getByRole("button", { name: "Add" }));

    await waitFor(() =>
      expect(post).toHaveBeenCalledWith("/api/v1/challenges/{challenge_id}/check-ins", {
        params: { path: { challenge_id: "read" } },
        body: { day: "2026-11-10", amount: "20.5" },
      }),
    );
  });

  it("says when nothing is asked today", async () => {
    mockToday(today([{ ...walk, state: "not_due", settled: null }]));
    show();
    expect(await screen.findByRole("heading", { name: "A day off" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Not asked today" })).toBeDisabled();
  });

  it("shows how long is left late in the day", async () => {
    vi.useFakeTimers({ toFake: ["Date"], now: new Date("2026-11-10T19:40:00Z") });
    mockToday(today([walk]));
    show();
    expect(await screen.findByText("2 h 20 min left")).toBeInTheDocument();
  });

  it("points to the crew tab when no challenge runs", async () => {
    mockToday(today([]));
    show();
    expect(await screen.findByRole("heading", { name: "No challenge yet" })).toBeInTheDocument();
  });
});

describe("hold button", () => {
  it("confirms only after a full hold", () => {
    vi.useFakeTimers();
    const confirm = vi.fn();
    render(<HoldButton label="Hold" doneLabel="Done" onConfirm={confirm} />);
    const button = screen.getByRole("button", { name: "Hold" });

    fireEvent.pointerDown(button, { button: 0 });
    act(() => vi.advanceTimersByTime(300));
    fireEvent.pointerUp(button);
    act(() => vi.advanceTimersByTime(600));
    expect(confirm).not.toHaveBeenCalled();

    fireEvent.pointerDown(button, { button: 0 });
    act(() => vi.advanceTimersByTime(600));
    expect(confirm).toHaveBeenCalledTimes(1);
    fireEvent.click(button, { detail: 1 }); // the click that follows a hold does nothing more
    expect(confirm).toHaveBeenCalledTimes(1);
  });
});

describe("month board", () => {
  const states = (done: number): TodayChallenge["state"][] =>
    Array.from({ length: 30 }, (_, i) => (i < done ? "done" : i === done ? "missed" : "future"));

  it("shows everyone's month with streaks and moves between months", async () => {
    const get = vi.spyOn(api, "GET").mockImplementation(((
      _path: string,
      options: { params: { query: { month: string } } },
    ) =>
      ok({
        days: Array.from(
          { length: 30 },
          (_, i) => `${options.params.query.month}-${String(i + 1).padStart(2, "0")}`,
        ),
        rows: [
          { member: person(ana), states: states(9), streak: 9 },
          { member: person(bogdan), states: states(3), streak: 0 },
        ],
      })) as never);
    vi.useFakeTimers({ toFake: ["Date"], now: new Date("2026-11-10T09:00:00Z") });
    renderRoutes([
      {
        path: "/",
        element: (
          <ChallengeBoard
            challengeId="walk"
            startDate="2026-11-01"
            endDate="2026-12-31"
            timeZone="Europe/Chisinau"
          />
        ),
      },
    ]);

    expect(await screen.findByRole("heading", { name: "November 2026" })).toBeInTheDocument();
    const grid = await screen.findByRole("table", { name: "The crew's month, November 2026" });
    expect(within(grid).getAllByText("Ana · 9")).toHaveLength(2); // once per half of the month
    expect(within(grid).getByRole("img", { name: "Bogdan, 4: missed" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Previous month" })).toBeDisabled();

    await userEvent.click(screen.getByRole("button", { name: "Next month" }));
    expect(await screen.findByRole("heading", { name: "December 2026" })).toBeInTheDocument();
    expect(get).toHaveBeenLastCalledWith("/api/v1/challenges/{challenge_id}/board", {
      params: { path: { challenge_id: "walk" }, query: { month: "2026-12" } },
    });
  });
});

describe("raised check-in button", () => {
  it("shows what is left and opens the check-in sheet", async () => {
    mockToday(
      today([walk, read, { ...walk, id: "gym", title: "Gym", state: "done", settled: true }]),
    );
    renderRoutes([
      {
        path: "/",
        element: <Shell />,
      },
    ]);

    await userEvent.click(await screen.findByRole("button", { name: "Check in (2)" }));
    const sheet = await screen.findByRole("dialog", { name: "What do you check in?" });
    expect(within(sheet).getByRole("heading", { name: "Walk" })).toBeInTheDocument();
    expect(within(sheet).getByRole("heading", { name: "Read" })).toBeInTheDocument();
    expect(within(sheet).queryByRole("heading", { name: "Gym" })).not.toBeInTheDocument();
  });

  it("is hidden when nothing runs today", async () => {
    mockToday(today([]));
    renderRoutes([{ path: "/", element: <Shell /> }]);
    expect(await screen.findByRole("navigation", { name: "Preview" })).toBeInTheDocument();
    await waitFor(() => expect(api.GET).toHaveBeenCalledWith("/api/v1/today"));
    expect(screen.queryByRole("button", { name: /Check in/ })).not.toBeInTheDocument();
  });
});

function Shell() {
  const checkIn = useCheckInAction(true);
  return (
    <>
      <TabBar
        label="Preview"
        tabs={[{ to: "/", label: "Today", icon: "sun", end: true }]}
        action={checkIn.action}
      />
      {checkIn.open && <CheckInSheet onClose={checkIn.close} />}
    </>
  );
}
