import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { renderScreen } from "@/test/render";

import { Avatar, AvatarStack, avatarColor, initials } from "./Avatar";
import { Button } from "./Button";
import { DayBar, DayBars, DayBarsAxis } from "./DayBars";
import { Dial } from "./Dial";
import { List, ListRow } from "./ListRow";
import { QrCode } from "./QrCode";
import { Sheet } from "./Sheet";
import { StatusPill } from "./StatusPill";
import { TabBar } from "./TabBar";
import { TextField } from "./TextField";
import { TruncatedText } from "./TruncatedText";

describe("Button", () => {
  it("is disabled and busy while loading", async () => {
    const onClick = vi.fn();
    render(
      <Button loading onClick={onClick}>
        Save
      </Button>,
    );
    const button = screen.getByRole("button", { name: "Save" });
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute("aria-busy", "true");
    await userEvent.click(button);
    expect(onClick).not.toHaveBeenCalled();
  });
});

describe("TextField", () => {
  it("links the error message to the input for screen readers", () => {
    render(<TextField label="Username" error="Taken." />);
    const input = screen.getByLabelText("Username");
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(input).toHaveAccessibleDescription("Taken.");
  });

  it("shows and hides a password with its eye button", async () => {
    render(<TextField label="Password" type="password" reveal="Show password" />);
    const input = screen.getByLabelText("Password");
    const eye = screen.getByRole("button", { name: "Show password" });
    expect(input).toHaveAttribute("type", "password");
    await userEvent.click(eye);
    expect(input).toHaveAttribute("type", "text");
    expect(eye).toHaveAttribute("aria-pressed", "true");
    await userEvent.click(eye);
    expect(input).toHaveAttribute("type", "password");
  });
});

describe("Sheet", () => {
  it("closes on Escape and with the close button", async () => {
    const onClose = vi.fn();
    render(
      <Sheet open onClose={onClose} title="Invite" closeLabel="Close">
        <p>content</p>
      </Sheet>,
    );
    expect(screen.getByRole("dialog", { name: "Invite" })).toBeInTheDocument();
    await userEvent.keyboard("{Escape}");
    await userEvent.click(screen.getByRole("button", { name: "Close" }));
    expect(onClose).toHaveBeenCalledTimes(2);
  });
});

describe("Avatar", () => {
  it("shows initials and a stable color for the same seed", () => {
    expect(initials("Ana Maria Popescu")).toBe("AP");
    expect(initials("dan")).toBe("D");
    expect(avatarColor("abc")).toBe(avatarColor("abc"));
    expect(avatarColor("abc")).toBeGreaterThanOrEqual(1);
    expect(avatarColor("abc")).toBeLessThanOrEqual(6);
    render(<Avatar name="Ana" seed="s1" />);
    expect(screen.getByRole("img", { name: "Ana" })).toHaveTextContent("A");
  });
});

describe("AvatarStack", () => {
  it("shows five avatars, then the rest as +N, under one accessible name", () => {
    const members = ["A", "B", "C", "D", "E", "F", "G"].map((name) => ({
      id: name,
      name,
      seed: name,
    }));
    render(<AvatarStack members={members} label="7 members" />);
    expect(screen.getByRole("img", { name: "7 members" })).toHaveTextContent("ABCDE+2");
  });
});

describe("StatusPill", () => {
  it("adds a check to success so meaning does not rest on color", () => {
    const { container } = render(<StatusPill tone="success">Done</StatusPill>);
    expect(container.querySelector("svg")).not.toBeNull();
    expect(screen.getByText("Done")).toBeInTheDocument();
  });
});

describe("ListRow", () => {
  it("makes the whole row a link when given `to`", () => {
    renderScreen(
      <List label="Members">
        <ListRow to="/crew/1" title="Bogdan" subtitle="Admin" />
      </List>,
    );
    expect(screen.getByRole("list", { name: "Members" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Bogdan/ })).toHaveAttribute("href", "/crew/1");
  });
});

describe("QrCode", () => {
  it("draws the code as a labelled image", () => {
    render(<QrCode value="https://example.com/join/abc" label="Invite QR code" />);
    const image = screen.getByRole("img", { name: "Invite QR code" });
    expect(image.querySelector("path")?.getAttribute("d")).toMatch(/^M\d+ \d+h1v1h-1z/);
  });
});

describe("DayBars", () => {
  it("reads as one summary, not a bar per day", () => {
    render(<DayBars states={["done", "missed", "todo", "future"]} label="Ana: 1 done, 1 missed" />);

    expect(screen.getByRole("img", { name: "Ana: 1 done, 1 missed" })).toBeInTheDocument();
    expect(screen.getAllByRole("img")).toHaveLength(1);
  });

  it("numbers the first day, every fifth, the last and today", () => {
    const days = Array.from({ length: 31 }, (_, i) => i + 1);
    const { container } = render(<DayBarsAxis days={days} todayIndex={6} />);

    expect(container.textContent).toBe(["1", "5", "7", "10", "15", "20", "25", "31"].join(""));
  });

  it("names a single bar when it has a label", () => {
    render(<DayBar state="missed" label="missed" />);

    expect(screen.getByRole("img", { name: "missed" })).toBeInTheDocument();
  });
});

describe("Dial", () => {
  it("numbers one arc per punishment; the mark has no numbers", () => {
    const { rerender } = render(<Dial count={5} label="A dial with 5 punishments" />);
    expect(screen.getByRole("img", { name: "A dial with 5 punishments" })).toBeInTheDocument();
    expect(screen.getByText("5")).toBeInTheDocument();
    rerender(<Dial size="sm" count={5} drawn={3} label="The mark" />);
    expect(screen.queryByText("5")).toBeNull();
  });
});

describe("TabBar", () => {
  it("shows a tab's badge, nine at most, and says it", async () => {
    const tabs = (count: number) => [
      { to: "/", label: "Today", icon: "sun" as const, end: true },
      {
        to: "/crew",
        label: "Crew",
        icon: "users" as const,
        badge: { count, label: `${count} new` },
      },
    ];
    const { unmount } = renderScreen(<TabBar label="Main" tabs={tabs(3)} />);
    expect(await screen.findByRole("link", { name: "Crew, 3 new" })).toHaveTextContent("3");
    expect(screen.getByRole("link", { name: "Today" })).toBeInTheDocument();
    unmount();

    renderScreen(<TabBar label="Main" tabs={tabs(12)} />);
    expect(await screen.findByRole("link", { name: "Crew, 12 new" })).toHaveTextContent("9+");
  });

  it("shows no badge at zero", async () => {
    renderScreen(
      <TabBar
        label="Main"
        tabs={[{ to: "/crew", label: "Crew", icon: "users", badge: { count: 0, label: "none" } }]}
      />,
    );
    expect(await screen.findByRole("link", { name: "Crew" })).toHaveTextContent(/^Crew$/);
  });
});

describe("TruncatedText", () => {
  const LONG = "Wash every dish in the house by hand tonight, then dry them too";

  /** jsdom lays nothing out: how wide the text is, and how wide its line. */
  function measure(line: HTMLElement, textWidth: number) {
    Object.defineProperty(line, "scrollWidth", { configurable: true, value: textWidth });
    Object.defineProperty(line, "clientWidth", { configurable: true, value: 100 });
  }
  const shown = (text: string) => screen.getAllByText(text).length;

  it("shows the whole of a cut text on tap; a second tap, a tap outside or Escape close it", async () => {
    render(
      <>
        <TruncatedText text={LONG} />
        <p>Outside</p>
      </>,
    );
    const line = screen.getByText(LONG);
    measure(line, 300);

    await userEvent.click(line);
    expect(shown(LONG)).toBe(2); // the line and the bubble
    await userEvent.click(line);
    await waitFor(() => expect(shown(LONG)).toBe(1));
    await userEvent.click(line);
    await userEvent.click(screen.getByText("Outside"));
    await waitFor(() => expect(shown(LONG)).toBe(1));
    await userEvent.click(line);
    await userEvent.keyboard("{Escape}");
    await waitFor(() => expect(shown(LONG)).toBe(1));
  });

  it("does nothing when the text fits, and keeps it whole for a mouse", async () => {
    render(<TruncatedText text="20 burpees" />);
    const line = screen.getByText("20 burpees");
    measure(line, 80);

    await userEvent.click(line);

    expect(shown("20 burpees")).toBe(1);
    expect(line).toHaveAttribute("title", "20 burpees");
  });
});
