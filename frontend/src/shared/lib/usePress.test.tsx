import { act, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { usePress } from "./usePress";

function Pressable({ onPress, onLongPress }: { onPress: () => void; onLongPress: () => void }) {
  const press = usePress({ onPress, onLongPress });
  return (
    <button type="button" {...press}>
      Fire
    </button>
  );
}

function setup() {
  const onPress = vi.fn();
  const onLongPress = vi.fn();
  render(<Pressable onPress={onPress} onLongPress={onLongPress} />);
  return { onPress, onLongPress, button: screen.getByRole("button", { name: "Fire" }) };
}

afterEach(() => vi.useRealTimers());

describe("usePress", () => {
  it("taps with a click, Enter and Space", async () => {
    const { onPress, onLongPress, button } = setup();
    await userEvent.click(button);
    button.focus();
    await userEvent.keyboard("{Enter}");
    await userEvent.keyboard(" ");
    expect(onPress).toHaveBeenCalledTimes(3);
    expect(onLongPress).not.toHaveBeenCalled();
  });

  it("holding still is a long press, and the click after it is not a tap", () => {
    vi.useFakeTimers();
    const { onPress, onLongPress, button } = setup();
    fireEvent.pointerDown(button, { clientX: 10, clientY: 10 });
    act(() => vi.advanceTimersByTime(500));
    fireEvent.pointerUp(button);
    fireEvent.click(button);
    expect(onLongPress).toHaveBeenCalledOnce();
    expect(onPress).not.toHaveBeenCalled();

    fireEvent.click(button); // the next tap counts again
    expect(onPress).toHaveBeenCalledOnce();
  });

  it("moving the finger (scrolling) cancels the hold", () => {
    vi.useFakeTimers();
    const { onLongPress, button } = setup();
    fireEvent.pointerDown(button, { clientX: 10, clientY: 10 });
    fireEvent.pointerMove(button, { clientX: 10, clientY: 40 });
    act(() => vi.advanceTimersByTime(600));
    expect(onLongPress).not.toHaveBeenCalled();
  });

  it("the context menu (right click, menu key) is a long press too, once", () => {
    vi.useFakeTimers();
    const { onPress, onLongPress, button } = setup();
    fireEvent.contextMenu(button);
    expect(onLongPress).toHaveBeenCalledOnce();
    fireEvent.click(button); // no finger was down: a later click is a tap
    expect(onPress).toHaveBeenCalledOnce();

    fireEvent.pointerDown(button, { clientX: 0, clientY: 0 });
    act(() => vi.advanceTimersByTime(500)); // Android: the timer, then its own context menu
    fireEvent.contextMenu(button);
    expect(onLongPress).toHaveBeenCalledTimes(2);
  });
});
