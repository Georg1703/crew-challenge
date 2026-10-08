import { act, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { holdOn, usePress } from "./usePress";

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

/** A pointer event with what holdOn reads, whether or not this jsdom knows PointerEvent. */
function pointer(target: Element, type: string, init: Record<string, unknown> = {}) {
  const event = new Event(type, { bubbles: true, cancelable: true });
  Object.assign(event, { pointerType: "touch", clientX: 0, clientY: 0, ...init });
  target.dispatchEvent(event);
  return event;
}

describe("holdOn", () => {
  function card() {
    const element = document.createElement("article");
    const tile = document.createElement("button"); // a proof tile, say
    const control = document.createElement("div"); // the reactions row: its own gestures
    control.append(document.createElement("button"));
    element.append(tile, control);
    document.body.append(element);
    const onLongPress = vi.fn();
    const onTile = vi.fn();
    tile.addEventListener("click", onTile);
    const stop = holdOn(element, onLongPress, { skip: control });
    return { element, tile, control, onLongPress, onTile, stop };
  }

  it("a finger held still on the card fires once, and the tap it ends with does nothing", () => {
    vi.useFakeTimers();
    const { tile, onLongPress, onTile, stop } = card();
    pointer(tile, "pointerdown");
    vi.advanceTimersByTime(500);
    pointer(tile, "pointerup");
    expect(pointer(tile, "contextmenu").defaultPrevented).toBe(true); // Android's menu
    tile.click();
    expect(onLongPress).toHaveBeenCalledOnce();
    expect(onTile).not.toHaveBeenCalled();
    tile.click(); // the next tap opens the tile again
    expect(onTile).toHaveBeenCalledOnce();
    stop();
  });

  it("leaves scrolling, the control's own buttons, a mouse and a right click alone", () => {
    vi.useFakeTimers();
    const { tile, control, onLongPress, stop } = card();
    pointer(tile, "pointerdown");
    pointer(tile, "pointermove", { clientY: 30 });
    pointer(control.firstElementChild as Element, "pointerdown");
    pointer(tile, "pointerdown", { pointerType: "mouse" });
    vi.advanceTimersByTime(600);
    expect(pointer(tile, "contextmenu").defaultPrevented).toBe(false);
    expect(onLongPress).not.toHaveBeenCalled();
    stop();
    pointer(tile, "pointerdown");
    vi.advanceTimersByTime(600);
    expect(onLongPress).not.toHaveBeenCalled(); // cleaned up
  });
});
