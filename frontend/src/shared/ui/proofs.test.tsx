import { act, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";

import { DayBar, DayBars, DayBarsAxis } from "./DayBars";
import { FeedItem, type FeedProof } from "./FeedItem";
import { List } from "./ListRow";
import { ProofAddTile, ProofTile } from "./ProofTile";
import { ProofViewer, type ViewerItem } from "./ProofViewer";
import { Sheet } from "./Sheet";
import { TabBar } from "./TabBar";
import { WeekStrip } from "./WeekStrip";

interface FakePlayer {
  config: { xhrSetup: (xhr: { withCredentials: boolean }) => void };
  source: string;
  media: HTMLMediaElement | null;
  handlers: Record<string, (event: unknown, data: { fatal: boolean }) => void>;
  destroy: () => void;
}

const players = vi.hoisted(() => [] as FakePlayer[]);

vi.mock("hls.js", () => ({
  default: class {
    static isSupported = () => true;
    static Events = { ERROR: "hlsError" };
    handlers: FakePlayer["handlers"] = {};
    source = "";
    media: HTMLMediaElement | null = null;
    destroy = vi.fn();
    constructor(public config: FakePlayer["config"]) {
      players.push(this);
    }
    on(event: string, handler: FakePlayer["handlers"][string]) {
      this.handlers[event] = handler;
    }
    loadSource(url: string) {
      this.source = url;
    }
    attachMedia(media: HTMLMediaElement) {
      this.media = media;
    }
  },
}));

afterEach(() => {
  players.length = 0;
  vi.restoreAllMocks();
});

describe("ProofTile", () => {
  it("opens and removes with its own buttons", async () => {
    const onOpen = vi.fn();
    const onRemove = vi.fn();
    render(
      <ProofTile
        kind="photo"
        src="/a.jpg"
        label="Photo by Ana"
        onOpen={onOpen}
        onRemove={onRemove}
        removeLabel="Remove photo"
      />,
    );

    await userEvent.click(screen.getByRole("button", { name: "Photo by Ana" }));
    await userEvent.click(screen.getByRole("button", { name: "Remove photo" }));

    expect(onOpen).toHaveBeenCalledOnce();
    expect(onRemove).toHaveBeenCalledOnce();
  });

  it("shows its state by a mark, and is a labelled picture when nothing opens it", () => {
    const marks = (element: React.ReactElement) => {
      const { container, unmount } = render(element);
      const count = container.querySelectorAll(".mark").length;
      unmount();
      return count;
    };

    expect(marks(<ProofTile kind="photo" src="/a.jpg" label="Photo" />)).toBe(0);
    expect(marks(<ProofTile kind="video" src="/a.jpg" label="Video" />)).toBe(1); // play
    expect(marks(<ProofTile kind="photo" state="uploading" progress={0.4} label="Up" />)).toBe(1);
    render(<ProofTile kind="video" state="processing" label="Video, being prepared" />);
    expect(screen.getByRole("img", { name: "Video, being prepared" })).toBeInTheDocument();
    expect(screen.queryByRole("button")).toBeNull();
  });
});

describe("FeedItem", () => {
  it("shows three proofs, then +N that opens the fourth", async () => {
    const onOpenProof = vi.fn();
    const proofs: FeedProof[] = Array.from({ length: 5 }, (_, i) => ({
      key: String(i),
      kind: "photo",
      state: "ready",
      src: `/${i}.jpg`,
      label: `Proof ${i + 1}`,
    }));
    render(
      <List label="Activity">
        <FeedItem
          name="Ana"
          seed="ana"
          text="Ana checked in Walk"
          time="5 min ago"
          proofs={proofs}
          onOpenProof={onOpenProof}
          moreLabel="2 more proofs"
        />
      </List>,
    );

    expect(screen.getAllByRole("button", { name: /^Proof/ })).toHaveLength(3);
    await userEvent.click(screen.getByRole("button", { name: "Proof 2" }));
    expect(onOpenProof).toHaveBeenLastCalledWith(1);
    await userEvent.click(screen.getByRole("button", { name: "2 more proofs" }));
    expect(onOpenProof).toHaveBeenLastCalledWith(3);
    expect(screen.getByRole("button", { name: "2 more proofs" })).toHaveTextContent("+2");
  });
});

const PHOTO: ViewerItem = { key: "a", kind: "photo", src: "/a.jpg", caption: "Ana, Walk" };
const VIDEO: ViewerItem = {
  key: "b",
  kind: "video",
  src: "/b.mp4",
  poster: "/b.jpg",
  caption: "Bogdan, Walk",
};

function Viewer({ items, onClose = () => {} }: { items: ViewerItem[]; onClose?: () => void }) {
  const [index, setIndex] = useState(0);
  return (
    <ProofViewer
      items={items}
      index={index}
      onIndexChange={setIndex}
      open
      onClose={onClose}
      label="Proofs"
      closeLabel="Close"
      previousLabel="Previous"
      nextLabel="Next"
    />
  );
}

describe("ProofViewer", () => {
  it("moves with the arrows and the keyboard, and closes on Escape", async () => {
    const onClose = vi.fn();
    render(<Viewer items={[PHOTO, VIDEO]} onClose={onClose} />);

    expect(screen.getByRole("dialog", { name: "Proofs" })).toHaveTextContent("1 / 2");
    expect(screen.queryByRole("button", { name: "Previous" })).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(screen.getByText("Bogdan, Walk")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Next" })).toBeNull();
    await userEvent.keyboard("{ArrowLeft}");
    expect(screen.getByText("Ana, Walk")).toBeInTheDocument();
    await userEvent.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("zooms a photo with a double tap or a pinch", async () => {
    render(<Viewer items={[PHOTO]} />);
    const photo = screen.getByRole("img", { name: "Ana, Walk" });
    const frame = photo.parentElement as HTMLElement;

    await userEvent.dblClick(photo);
    expect(frame).toHaveAttribute("data-zoomed", "true");
    expect(photo.style.transform).toContain("scale(2.5)");
    await userEvent.dblClick(photo);
    expect(frame).not.toHaveAttribute("data-zoomed");

    fireEvent.pointerDown(frame, { pointerId: 1, clientX: 100, clientY: 100 });
    fireEvent.pointerDown(frame, { pointerId: 2, clientX: 200, clientY: 100 });
    fireEvent.pointerMove(frame, { pointerId: 2, clientX: 300, clientY: 100 });
    expect(photo.style.transform).toContain("scale(2)");
  });

  it("plays the original video inline and muted when there is no playlist", () => {
    render(<Viewer items={[VIDEO]} />);
    const video = screen.getByLabelText("Bogdan, Walk") as HTMLVideoElement;

    expect(video.src).toMatch(/\/b\.mp4$/);
    expect(video.muted).toBe(true);
    expect(video).toHaveAttribute("playsinline");
    expect(players).toHaveLength(0);
  });

  it("plays the playlist natively where the browser can (Safari)", () => {
    vi.spyOn(HTMLMediaElement.prototype, "canPlayType").mockReturnValue("maybe");
    render(<Viewer items={[{ ...VIDEO, hlsSrc: "/b/hls.m3u8" }]} />);

    expect((screen.getByLabelText("Bogdan, Walk") as HTMLVideoElement).src).toMatch(
      /\/b\/hls\.m3u8$/,
    );
    expect(players).toHaveLength(0);
  });

  it("loads hls.js elsewhere, with the media cookies, and falls back to the original", async () => {
    render(<Viewer items={[{ ...VIDEO, hlsSrc: "/b/hls.m3u8" }]} />);
    const video = screen.getByLabelText("Bogdan, Walk") as HTMLVideoElement;

    await vi.waitFor(() => expect(players).toHaveLength(1));
    const player = players[0] as FakePlayer;
    expect(player.media).toBe(video);
    expect(player.source).toBe("/b/hls.m3u8");
    const xhr = { withCredentials: false };
    player.config.xhrSetup(xhr);
    expect(xhr.withCredentials).toBe(true);

    act(() => player.handlers.hlsError?.({}, { fatal: true }));
    expect(player.destroy).toHaveBeenCalled();
    expect(video.src).toMatch(/\/b\.mp4$/);
  });
});

describe("proof dots", () => {
  it("adds a dot under each day with proof, keeping one summary for screen readers", () => {
    const { container } = render(
      <DayBars states={["done", "done", "missed"]} proofs={[true, false, false]} label="Ana" />,
    );

    expect(screen.getAllByRole("img")).toHaveLength(1);
    expect(container.querySelectorAll(".dot")).toHaveLength(1);
  });

  it("marks a legend bar and the days of a week strip", () => {
    const { container } = render(
      <>
        <DayBar state="done" label="done, with proof" proof />
        <WeekStrip
          label="This week"
          days={[
            { key: "1", letter: "M", name: "Monday: done, with proof", state: "done", proof: true },
            { key: "2", letter: "T", name: "Tuesday: done", state: "done" },
          ]}
        />
      </>,
    );

    expect(container.querySelectorAll(".dot")).toHaveLength(2);
  });
});

describe("ProofAddTile", () => {
  it("opens the picker for its kinds and hands over the file, ready for the same file again", async () => {
    const onPick = vi.fn();
    const { container } = render(
      <ProofAddTile accept="video/*" label="Add a video" onPick={onPick} />,
    );
    const input = container.querySelector("input") as HTMLInputElement;
    const file = new File(["v"], "clip.mp4", { type: "video/mp4" });

    expect(input).toHaveAttribute("accept", "video/*");
    expect(screen.getByRole("button", { name: "Add a video" })).toBeInTheDocument();
    await userEvent.upload(input, file);

    expect(onPick).toHaveBeenCalledWith(file);
    expect(input.value).toBe("");
  });
});

describe("TabBar action progress", () => {
  it("draws a ring only while something runs", () => {
    const action = { label: "Check in", icon: "check" as const, onClick: () => undefined };
    const { container, rerender } = renderScreenless(
      <TabBar label="Nav" tabs={[]} action={action} />,
    );
    expect(container.querySelector(".progress")).toBeNull();

    rerender(<TabBar label="Nav" tabs={[]} action={{ ...action, progress: 0.3 }} />);
    expect(container.querySelector(".progress")).not.toBeNull();
  });
});

/** TabBar renders NavLinks, which need a router. */
function renderScreenless(element: React.ReactElement) {
  const wrap = (child: React.ReactElement) => <MemoryRouter>{child}</MemoryRouter>;
  const result = render(wrap(element));
  return { ...result, rerender: (next: React.ReactElement) => result.rerender(wrap(next)) };
}

describe("picking a day", () => {
  it("makes each day number a named button", async () => {
    const onPick = vi.fn();
    render(<DayBarsAxis days={[1, 2, 3]} onPick={onPick} labels={["Mon 1", "Tue 2", "Wed 3"]} />);

    await userEvent.click(screen.getByRole("button", { name: "Tue 2" }));
    expect(onPick).toHaveBeenCalledWith(1);
  });

  it("picks the day under the finger on a row of bars", () => {
    const onPick = vi.fn();
    render(<DayBars states={["done", "done", "done", "done"]} label="Ana" onPick={onPick} />);
    const row = screen.getByRole("img", { name: "Ana" });
    vi.spyOn(row, "getBoundingClientRect").mockReturnValue({ left: 0, width: 400 } as DOMRect);

    fireEvent.click(row, { clientX: 250 });
    expect(onPick).toHaveBeenCalledWith(2);
  });
});

describe("a viewer opened from a sheet", () => {
  it("closes alone on Escape; the sheet stays", async () => {
    const closeSheet = vi.fn();
    const closeViewer = vi.fn();
    render(
      <Sheet open onClose={closeSheet} title="Monday" closeLabel="Close sheet">
        <ProofViewer
          items={[PHOTO]}
          index={0}
          onIndexChange={() => undefined}
          open
          onClose={closeViewer}
          label="Proofs"
          closeLabel="Close"
          previousLabel="Previous"
          nextLabel="Next"
        />
      </Sheet>,
    );

    await userEvent.keyboard("{Escape}");

    expect(closeViewer).toHaveBeenCalledOnce();
    expect(closeSheet).not.toHaveBeenCalled();
  });
});
