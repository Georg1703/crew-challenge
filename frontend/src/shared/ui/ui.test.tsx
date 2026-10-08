import { render, screen } from "@testing-library/react";
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
import { TextField } from "./TextField";

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
