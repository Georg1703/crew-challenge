import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Avatar, avatarColor, initials } from "./Avatar";
import { Button } from "./Button";
import { Sheet } from "./Sheet";
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
