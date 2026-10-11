import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/api";
import type { Proof } from "@/features/proofs";
import type * as UI from "@/shared/ui";
import { ana, bogdan, meAs } from "@/test/fixtures";
import { fail, ok, renderScreen } from "@/test/render";

import { Comments, type Comment } from ".";
import { deletable } from "./thread";

afterEach(() => vi.restoreAllMocks());

// The full picker (Emoji Mart) is loaded on demand: here it is one button that picks a fire.
vi.mock("@/shared/ui", async (load) => ({
  ...(await load<typeof UI>()),
  EmojiPicker: ({ onPick }: { onPick: (emoji: string) => void }) => (
    <button type="button" onClick={() => onPick("\u{1F525}")}>
      Pick a fire
    </button>
  ),
}));

const photo = (id: string, status: Proof["status"] = "ready", posted = false): Proof => ({
  id,
  kind: "photo",
  status,
  url: status === "ready" ? `/media/${id}.gif` : null,
  hls_url: null,
  thumb_url: status === "ready" ? `/media/${id}-thumb.jpg` : null,
  phone_thumb_url: null,
  created_at: new Date(NOW).toISOString(),
  duration: null,
  posted,
});

const NOW = Date.parse("2026-11-10T08:00:00Z");
const NONE = { groups: [], mine: null };

const say = (id: string, text: string, over: Partial<Comment> = {}): Comment => ({
  id,
  member_id: bogdan.id,
  parent_id: null,
  text,
  created_at: new Date(NOW - 10 * 60_000).toISOString(),
  reactions: NONE,
  proofs: [],
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

function serve(thread: Comment[], drafts: Proof[] = []) {
  vi.spyOn(api, "GET").mockImplementation(((path: string) =>
    path === "/api/v1/me"
      ? ok(meAs(ana))
      : path === "/api/v1/comments/{target}/{target_id}"
        ? ok({ results: thread, drafts })
        : ok({})) as never);
}

function show(onRead?: () => void) {
  return renderScreen(
    <Comments
      target="entry"
      id="e1"
      people={[ana, bogdan]}
      timeZone="Europe/Chisinau"
      onRead={onRead}
    />,
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
      say("c", "Mersi", { member_id: ana.id, parent_id: "a" }),
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

  it("offers Reply and Copy always, Delete on my fresh message", async () => {
    serve([
      say("a", "Bravo!"),
      say("b", "Deep", { parent_id: "a" }),
      say("c", "Typo here", { member_id: ana.id, created_at: new Date().toISOString() }),
    ]);
    show();

    const top = await menuOf("Bravo!");
    expect(within(top).getByRole("menuitem", { name: "Reply" })).toBeInTheDocument();
    expect(within(top).getByRole("menuitem", { name: "Copy text" })).toBeInTheDocument();
    expect(within(top).queryByRole("menuitem", { name: "Delete" })).not.toBeInTheDocument();
    await closeMenu();

    const deep = await menuOf("Deep"); // a reply to a reply takes replies too
    expect(within(deep).getByRole("menuitem", { name: "Reply" })).toBeInTheDocument();
    await closeMenu();

    const mine = await menuOf("Typo here");
    expect(within(mine).getByRole("menuitem", { name: "Delete" })).toBeInTheDocument();
  });

  it("replies with the box showing the quote, then empties it", async () => {
    serve([say("a", "Bravo!")]);
    const post = vi
      .spyOn(api, "POST")
      .mockImplementation((() =>
        ok(say("r", "Mersi", { member_id: ana.id, parent_id: "a" }), 201)) as never);
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

  it("marks the chat read when it opens", async () => {
    serve([say("a", "Bravo!")]);
    const put = vi.spyOn(api, "PUT").mockImplementation((() => ok(undefined, 204)) as never);
    const onRead = vi.fn();
    show(onRead);

    await waitFor(() => expect(onRead).toHaveBeenCalledOnce());
    expect(put).toHaveBeenCalledWith("/api/v1/comments/{target}/{target_id}/read", {
      params: { path: { target: "entry", target_id: "e1" } },
    });
  });

  it("keeps the text when sending fails", async () => {
    serve([]);
    vi.spyOn(api, "POST").mockImplementation((() =>
      fail(404, { code: "target_not_found" })) as never);
    show();

    expect(await screen.findByText("No comments yet. Say something nice.")).toBeInTheDocument();
    const box = screen.getByRole("textbox", { name: "Comment" });
    expect(screen.getByRole("button", { name: "Send" })).toBeDisabled();
    await userEvent.type(box, "Hello");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findByText("This is not here any more.")).toBeInTheDocument();
    expect(box).toHaveValue("Hello");
  });

  it("waits for a photo that uploads, then sends it alone", async () => {
    serve([], [photo("p1", "uploading")]);
    const { unmount } = show();
    const box = await screen.findByRole("textbox", { name: "Comment" });
    await userEvent.type(box, "Look");
    expect(screen.getByRole("button", { name: "Send" })).toBeDisabled(); // still uploading
    unmount();
    vi.restoreAllMocks();

    serve([], [photo("p1")]);
    const post = vi
      .spyOn(api, "POST")
      .mockImplementation((() =>
        ok(
          say("r", "", { member_id: ana.id, proofs: [photo("p1", "ready", true)] }),
          201,
        )) as never);
    show();
    const send = screen.getByRole("button", { name: "Send" });
    await waitFor(() => expect(send).toBeEnabled()); // a photo alone is a whole message
    await userEvent.click(send);
    await waitFor(() =>
      expect(post).toHaveBeenCalledWith("/api/v1/comments/{target}/{target_id}", {
        params: { path: { target: "entry", target_id: "e1" } },
        body: { text: "" },
      }),
    );
  });

  it("shows a comment's photos in its bubble, and quotes one with no text as a photo", async () => {
    serve([
      say("a", "", { proofs: [photo("g1", "ready", true)] }),
      say("b", "Ha!", { member_id: ana.id, parent_id: "a" }),
    ]);
    show();

    const reply = await message("Ha!");
    expect(
      within(reply).getByRole("button", { name: "Go to the comment it answers" }),
    ).toHaveTextContent("Photo");
    const quoted = screen.getAllByRole("article")[0];
    if (!quoted) throw new Error("no first message");
    expect(within(quoted).getAllByRole("button").length).toBeGreaterThan(1); // its photo
  });

  it("puts an emoji where the cursor is", async () => {
    serve([]);
    show();
    const box = await screen.findByRole("textbox", { name: "Comment" });
    await userEvent.type(box, "Bravo ");
    await userEvent.click(screen.getByRole("button", { name: "Emoji" }));
    await userEvent.click(await screen.findByRole("button", { name: "Pick a fire" }));
    await waitFor(() => expect(box).toHaveValue("Bravo \u{1F525}"));
  });
});
