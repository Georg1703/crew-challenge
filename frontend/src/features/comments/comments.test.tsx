import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/api";
import { ana, bogdan, meAs } from "@/test/fixtures";
import { fail, ok, renderScreen } from "@/test/render";

import { Comments, type Comment } from ".";
import { deletable } from "./thread";

afterEach(() => vi.restoreAllMocks());

const NOW = Date.parse("2026-11-10T08:00:00Z");
const NONE = { groups: [], mine: null };

const say = (id: string, text: string, over: Partial<Comment> = {}): Comment => ({
  id,
  member_id: bogdan.id,
  parent_id: null,
  level: 1,
  text,
  created_at: new Date(NOW - 10 * 60_000).toISOString(),
  reactions: NONE,
  ...over,
});

describe("deletable", () => {
  const mine = say("m", "typo", { member_id: ana.id, created_at: new Date(NOW).toISOString() });
  it("is mine, without replies, in its first minute", () => {
    expect(deletable(mine, false, ana.id, NOW + 59_000)).toBe(true);
    expect(deletable(mine, false, ana.id, NOW + 61_000)).toBe(false);
    expect(deletable(mine, true, ana.id, NOW + 1_000)).toBe(false);
    expect(deletable(mine, false, bogdan.id, NOW + 1_000)).toBe(false);
  });
});

function serve(thread: Comment[]) {
  vi.spyOn(api, "GET").mockImplementation(((path: string) =>
    path === "/api/v1/me"
      ? ok(meAs(ana))
      : path === "/api/v1/comments/{target}/{target_id}"
        ? ok({ results: thread })
        : ok({})) as never);
}

function show() {
  return renderScreen(
    <Comments target="entry" id="e1" people={[ana, bogdan]} timeZone="Europe/Chisinau" />,
  );
}

/** The message itself (a quote of it, in a reply, comes later in the page). */
const message = async (text: string) => {
  const found = (await screen.findAllByText(text))[0]?.closest("article");
  if (!found) throw new Error(`no message "${text}"`);
  return found as HTMLElement;
};

/** Open a message's menu with its react button (a computer; a phone holds the message). */
async function menuOf(text: string) {
  await userEvent.click(within(await message(text)).getByRole("button", { name: "React" }));
  return screen.findByRole("menu", { name: "React" });
}

async function closeMenu() {
  await userEvent.keyboard("{Escape}");
  await waitFor(() => expect(screen.queryByRole("menu")).not.toBeInTheDocument());
}

describe("Comments", () => {
  it("draws a chat: a writer's name once per run, mine without it, a reply with its quote", async () => {
    serve([
      say("a", "Bravo!"),
      say("b", "Five in a row"),
      say("c", "Mersi", { member_id: ana.id, parent_id: "a", level: 2 }),
    ]);
    const jump = vi.spyOn(Element.prototype, "scrollIntoView");
    show();

    expect(await screen.findAllByText("Bogdan")).toHaveLength(2); // the run's name, the quote's
    const mine = await message("Mersi");
    expect(within(mine).queryByText("You")).not.toBeInTheDocument(); // no name on mine
    await userEvent.click(
      within(mine).getByRole("button", { name: "Go to the comment it answers" }),
    );
    expect(jump).toHaveBeenCalled();
    expect(jump.mock.contexts[0]).toBe(await message("Bravo!"));
  });

  it("offers Reply above level 5, Copy always, Delete on my fresh message", async () => {
    serve([
      say("a", "Bravo!"),
      say("b", "Deep", { parent_id: "a", level: 5 }),
      say("c", "Typo here", { member_id: ana.id, created_at: new Date().toISOString() }),
    ]);
    show();

    const top = await menuOf("Bravo!");
    expect(within(top).getByRole("menuitem", { name: "Reply" })).toBeInTheDocument();
    expect(within(top).getByRole("menuitem", { name: "Copy text" })).toBeInTheDocument();
    expect(within(top).queryByRole("menuitem", { name: "Delete" })).not.toBeInTheDocument();
    await closeMenu();

    const deep = await menuOf("Deep");
    expect(within(deep).queryByRole("menuitem", { name: "Reply" })).not.toBeInTheDocument();
    await closeMenu();

    const mine = await menuOf("Typo here");
    expect(within(mine).getByRole("menuitem", { name: "Delete" })).toBeInTheDocument();
  });

  it("replies with the box showing the quote, then empties it", async () => {
    serve([say("a", "Bravo!")]);
    const post = vi
      .spyOn(api, "POST")
      .mockImplementation((() =>
        ok(say("r", "Mersi", { member_id: ana.id, parent_id: "a", level: 2 }), 201)) as never);
    show();

    await userEvent.click(within(await message("Bravo!")).getByRole("button", { name: "Reply" }));
    const box = screen.getByRole("textbox", { name: "Comment" });
    expect(box).toHaveFocus();
    expect(screen.getByRole("button", { name: "Stop replying" })).toBeInTheDocument();
    await userEvent.type(box, "  Mersi ");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));

    await waitFor(() => expect(box).toHaveValue(""));
    expect(post).toHaveBeenCalledWith("/api/v1/comments/{target}/{target_id}", {
      params: { path: { target: "entry", target_id: "e1" } },
      body: { text: "Mersi", parent_id: "a" },
    });
    expect(screen.queryByRole("button", { name: "Stop replying" })).not.toBeInTheDocument();
    expect(await message("Mersi")).toBeInTheDocument();
  });

  it("keeps the text when sending fails", async () => {
    serve([]);
    vi.spyOn(api, "POST").mockImplementation((() =>
      fail(409, { code: "reply_too_deep" })) as never);
    show();

    expect(await screen.findByText("No comments yet. Say something nice.")).toBeInTheDocument();
    const box = screen.getByRole("textbox", { name: "Comment" });
    expect(screen.getByRole("button", { name: "Send" })).toBeDisabled();
    await userEvent.type(box, "Hello");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findByText("Replies go 5 levels deep at most.")).toBeInTheDocument();
    expect(box).toHaveValue("Hello");
  });
});
