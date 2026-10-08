import { act, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/api";
import { ana, bogdan, meAs } from "@/test/fixtures";
import { fail, ok, renderScreen } from "@/test/render";

import { applyReaction, Reactions, type ReactionSummary } from ".";

const FIRE = "\u{1F525}";
const CLAP = "\u{1F44F}";
const THUMBS = "\u{1F44D}";
const ID = "c1";

afterEach(() => vi.restoreAllMocks());

describe("applyReaction", () => {
  const summary: ReactionSummary = {
    groups: [
      { emoji: CLAP, member_ids: [bogdan.id, ana.id] },
      { emoji: FIRE, member_ids: [bogdan.id] },
    ],
    mine: CLAP,
  };

  it("moves my reaction to the new emoji, last, and drops empty groups", () => {
    expect(applyReaction(summary, ana.id, FIRE)).toEqual({
      groups: [
        { emoji: CLAP, member_ids: [bogdan.id] },
        { emoji: FIRE, member_ids: [bogdan.id, ana.id] },
      ],
      mine: FIRE,
    });
    expect(applyReaction(summary, bogdan.id, null).groups).toEqual([
      { emoji: CLAP, member_ids: [ana.id] },
    ]);
    expect(applyReaction({ groups: [], mine: null }, ana.id, THUMBS)).toEqual({
      groups: [{ emoji: THUMBS, member_ids: [ana.id] }],
      mine: THUMBS,
    });
  });
});

/** The owner of the data: keeps the summary in state, like the feed keeps it in its cache. */
function Owner({ initial }: { initial: ReactionSummary }) {
  const [summary, setSummary] = useState(initial);
  return (
    <Reactions
      target="check_in"
      id={ID}
      summary={summary}
      people={[ana, bogdan]}
      onChange={setSummary}
    />
  );
}

function asAna() {
  vi.spyOn(api, "GET").mockImplementation(((path: string) =>
    path === "/api/v1/me" ? ok(meAs(ana)) : ok({})) as never);
}

describe("Reactions", () => {
  it("names chips by emoji and people, and a tap on yours takes it back", async () => {
    asAna();
    const remove = vi
      .spyOn(api, "DELETE")
      .mockImplementation((() =>
        ok({ groups: [{ emoji: FIRE, member_ids: [bogdan.id] }], mine: null })) as never);
    renderScreen(
      <Owner
        initial={{ groups: [{ emoji: FIRE, member_ids: [bogdan.id, ana.id] }], mine: FIRE }}
      />,
    );

    const chip = await screen.findByRole("button", { name: `${FIRE}, from Bogdan and you` });
    expect(chip).toHaveAttribute("aria-pressed", "true");
    await userEvent.click(chip);

    expect(remove).toHaveBeenCalledWith("/api/v1/reactions/{target}/{target_id}", {
      params: { path: { target: "check_in", target_id: ID } },
    });
    expect(await screen.findByRole("button", { name: `${FIRE}, from Bogdan` })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
  });

  it("reacts from the quick row at once, and rolls back with a message if it fails", async () => {
    asAna();
    let answer: (value: unknown) => void = () => {};
    vi.spyOn(api, "PUT").mockImplementation(
      (() => new Promise((resolve) => (answer = resolve))) as never,
    );
    renderScreen(<Owner initial={{ groups: [], mine: null }} />);

    await userEvent.click(await screen.findByRole("button", { name: "React" }));
    await userEvent.click(screen.getByRole("menuitemradio", { name: THUMBS }));
    // Optimistic: the chip is there before the server answers.
    expect(screen.getByRole("button", { name: `${THUMBS}, from you` })).toBeInTheDocument();

    answer(await fail(404, { code: "target_not_found" }));
    expect(await screen.findByText("You can't react to this any more.")).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.queryByRole("button", { name: `${THUMBS}, from you` })).not.toBeInTheDocument(),
    );
  });

  it("opens the quick row when the card around it is held (phones)", async () => {
    asAna();
    renderScreen(
      <article>
        <p>Bogdan checked in</p>
        <Owner initial={{ groups: [], mine: null }} />
      </article>,
    );
    await screen.findByRole("button", { name: "React" });

    vi.useFakeTimers();
    const press = new Event("pointerdown", { bubbles: true });
    Object.assign(press, { pointerType: "touch", clientX: 0, clientY: 0 });
    screen.getByText("Bogdan checked in").dispatchEvent(press);
    act(() => vi.advanceTimersByTime(500));
    vi.useRealTimers();

    expect(screen.getByRole("button", { name: "React" })).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("menuitemradio", { name: THUMBS })).toBeInTheDocument();
  });

  it("lists who reacted, from the quick row", async () => {
    asAna();
    renderScreen(
      <Owner
        initial={{
          groups: [
            { emoji: CLAP, member_ids: [bogdan.id] },
            { emoji: FIRE, member_ids: [ana.id] },
          ],
          mine: FIRE,
        }}
      />,
    );

    await userEvent.click(await screen.findByRole("button", { name: "React" }));
    await userEvent.click(screen.getByRole("menuitem", { name: "Who reacted" }));

    const sheet = await screen.findByRole("dialog", { name: "2 reactions" });
    const rows = within(sheet).getAllByRole("listitem");
    expect(rows.map((row) => row.textContent)).toEqual([`BBogdan${CLAP}`, `AYou${FIRE}`]);
  });
});
