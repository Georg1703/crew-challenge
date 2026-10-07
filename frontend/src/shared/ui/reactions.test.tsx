import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useRef, useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { EmojiPicker, type EmojiPickerTexts } from "./EmojiPicker";
import { ReactionChips, type ReactionChip } from "./ReactionChips";
import { ReactionMenu } from "./ReactionMenu";

const FIRE = "\u{1F525}";
const CLAP = "\u{1F44F}";
const people = ["Ana", "Bogdan", "Cristina", "Dan", "Elena"].map((name) => ({
  id: name,
  name,
  seed: name,
}));

const picked = vi.hoisted(() => ({ props: null as null | Record<string, unknown> }));
vi.mock("emoji-mart", () => ({
  // Called with `new`: a function that returns an object makes `new` return that object.
  Picker: function Picker(props: Record<string, unknown>) {
    picked.props = props;
    const element = document.createElement("div");
    element.setAttribute("data-testid", "emoji-mart");
    return element;
  },
}));
vi.mock("@emoji-mart/data", () => ({ default: { emojis: {} } }));

afterEach(() => {
  vi.useRealTimers();
  picked.props = null;
});

describe("ReactionChips", () => {
  const chips: ReactionChip[] = [
    { emoji: CLAP, people: people.slice(1), mine: false, label: "Clap, from 4" },
    { emoji: FIRE, people: people.slice(0, 1), mine: true, label: "Fire, from you" },
  ];

  it("shows each emoji with who used it, or how many, and marks yours", () => {
    render(<ReactionChips chips={chips} onToggle={() => {}} onHold={() => {}} />);
    const clap = screen.getByRole("button", { name: "Clap, from 4" });
    expect(clap).toHaveAttribute("aria-pressed", "false");
    expect(clap).toHaveTextContent("4");
    const fire = screen.getByRole("button", { name: "Fire, from you" });
    expect(fire).toHaveAttribute("aria-pressed", "true");
    expect(fire).toHaveTextContent("A"); // one person: their avatar
  });

  it("a tap toggles that emoji; holding asks who reacted", () => {
    vi.useFakeTimers();
    const onToggle = vi.fn();
    const onHold = vi.fn();
    render(<ReactionChips chips={chips} onToggle={onToggle} onHold={onHold} />);
    const fire = screen.getByRole("button", { name: "Fire, from you" });

    fireEvent.click(fire);
    expect(onToggle).toHaveBeenCalledWith(FIRE, expect.anything()); // and where it was

    fireEvent.pointerDown(fire, { clientX: 0, clientY: 0 });
    act(() => vi.advanceTimersByTime(500));
    fireEvent.click(fire);
    expect(onHold).toHaveBeenCalledWith(FIRE);
    expect(onToggle).toHaveBeenCalledOnce();
  });
});

function Menu({ onPick = () => {}, onMore = () => {}, onWho = () => {} }) {
  const [open, setOpen] = useState(false);
  const opener = useRef<HTMLButtonElement>(null);
  return (
    <>
      <button type="button" ref={opener} onClick={() => setOpen((v) => !v)}>
        React
      </button>
      <ReactionMenu
        open={open}
        onClose={() => setOpen(false)}
        label="Quick reactions"
        emojis={[FIRE, CLAP]}
        selected={CLAP}
        onPick={onPick}
        moreLabel="More emojis"
        onMore={onMore}
        whoLabel="Who reacted"
        onWho={onWho}
        anchor={opener}
      />
      <p>Outside</p>
    </>
  );
}

describe("ReactionMenu", () => {
  it("opens with focus inside, picks and closes, and gives focus back", async () => {
    const onPick = vi.fn();
    render(<Menu onPick={onPick} />);
    const opener = screen.getByRole("button", { name: "React" });
    await userEvent.click(opener);

    const menu = screen.getByRole("menu", { name: "Quick reactions" });
    expect(screen.getByRole("menuitemradio", { name: FIRE })).toHaveFocus();
    expect(screen.getByRole("menuitemradio", { name: CLAP })).toHaveAttribute(
      "aria-checked",
      "true",
    );
    await userEvent.click(screen.getByRole("menuitemradio", { name: FIRE }));

    expect(onPick).toHaveBeenCalledWith(FIRE, expect.anything());
    await waitFor(() => expect(menu).not.toBeInTheDocument());
    expect(opener).toHaveFocus();
  });

  it("closes on Escape, a tap outside and the opener; + and who reacted call back", async () => {
    const onMore = vi.fn();
    const onWho = vi.fn();
    render(<Menu onMore={onMore} onWho={onWho} />);
    const opener = screen.getByRole("button", { name: "React" });

    await userEvent.click(opener);
    await userEvent.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("menu")).not.toBeInTheDocument());

    await userEvent.click(opener);
    await userEvent.click(screen.getByText("Outside"));
    await waitFor(() => expect(screen.queryByRole("menu")).not.toBeInTheDocument());

    await userEvent.click(opener);
    await userEvent.click(opener); // toggles, not close-and-reopen
    await waitFor(() => expect(screen.queryByRole("menu")).not.toBeInTheDocument());

    await userEvent.click(opener);
    await userEvent.click(screen.getByRole("menuitem", { name: "More emojis" }));
    await userEvent.click(opener);
    await userEvent.click(screen.getByRole("menuitem", { name: "Who reacted" }));
    expect(onMore).toHaveBeenCalledOnce();
    expect(onWho).toHaveBeenCalledOnce();
  });
});

const TEXTS = { search: "Caută" } as unknown as EmojiPickerTexts;

describe("EmojiPicker", () => {
  it("loads Emoji Mart on demand with our texts and hands back the native emoji", async () => {
    const onPick = vi.fn();
    render(<EmojiPicker texts={TEXTS} onPick={onPick} errorText="Failed" retryLabel="Retry" />);

    await waitFor(() => expect(screen.getByTestId("emoji-mart")).toBeVisible());
    const props = picked.props as Record<string, unknown>;
    expect(props).toMatchObject({ i18n: TEXTS, set: "native", emojiButtonSize: 44 });
    (props.onEmojiSelect as (e: { native: string }) => void)({ native: FIRE });
    expect(onPick).toHaveBeenCalledWith(FIRE);
  });
});
