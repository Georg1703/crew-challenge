import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it, vi } from "vitest";

import { ChallengeChip } from "./ChallengeChip";
import { DayDivider } from "./DayDivider";
import { FeedCard } from "./FeedCard";
import { MiniWeek } from "./MiniWeek";
import { ProofMosaic, type FeedProof } from "./ProofMosaic";
import { ProofTile } from "./ProofTile";
import { StatGroup } from "./StatGroup";
import { StoryAvatar } from "./StoryAvatar";

const proofs = (count: number): FeedProof[] =>
  Array.from({ length: count }, (_, i) => ({
    key: String(i),
    kind: "photo",
    state: "ready",
    src: `/p${i}.jpg`,
    label: `Proof ${i + 1}`,
  }));

describe("StoryAvatar", () => {
  it("draws one segment per challenge due today", () => {
    const { container } = render(
      <StoryAvatar
        name="Ana Pop"
        seed="ana"
        segments={["done", "started", "todo"]}
        title="Ana"
        subtitle="1/3"
        label="Ana, 1 of 3"
      />,
    );
    expect(screen.getByRole("img", { name: "Ana, 1 of 3" })).toBeInTheDocument();
    expect(container.querySelectorAll("circle")).toHaveLength(3);
    expect(screen.getByText("AP")).toBeInTheDocument();
    expect(screen.getByText("1/3")).toBeInTheDocument();
  });

  it("draws a plain ring when nothing is due, and caps the new proofs count", () => {
    const { container } = render(
      <StoryAvatar name="Dan" seed="dan" segments={[]} fresh={12} label="Dan" />,
    );
    expect(container.querySelectorAll("circle")).toHaveLength(1);
    expect(screen.getByText("9+")).toBeInTheDocument();
  });

  it("is a link to the member's page with `to`", () => {
    render(
      <MemoryRouter>
        <StoryAvatar
          name="Ana"
          seed="ana"
          segments={["done"]}
          label="Ana, done"
          to="/crew/members/1"
        />
      </MemoryRouter>,
    );
    expect(screen.getByRole("link", { name: "Ana, done" })).toHaveAttribute(
      "href",
      "/crew/members/1",
    );
  });
});

describe("ProofMosaic", () => {
  it.each([1, 2, 3])("shows %i proofs without a more button", (count) => {
    render(<ProofMosaic proofs={proofs(count)} onOpen={() => {}} />);
    expect(screen.getAllByRole("button")).toHaveLength(count);
  });

  it.each([
    [4, "+1"],
    [6, "+3"],
  ])("shows three of %i proofs and the rest as %s", (count, more) => {
    render(<ProofMosaic proofs={proofs(count)} onOpen={() => {}} moreLabel="More proofs" />);
    expect(screen.getByRole("button", { name: "More proofs" })).toHaveTextContent(more);
    expect(screen.queryByRole("button", { name: "Proof 4" })).not.toBeInTheDocument();
  });

  it("opens the viewer at the tapped proof, and at the first hidden one from +N", async () => {
    const onOpen = vi.fn();
    render(<ProofMosaic proofs={proofs(5)} onOpen={onOpen} moreLabel="2 more proofs" />);
    await userEvent.click(screen.getByRole("button", { name: "Proof 2" }));
    await userEvent.click(screen.getByRole("button", { name: "2 more proofs" }));
    expect(onOpen.mock.calls).toEqual([[1], [3]]);
  });

  it.each([
    [1, ["full"]],
    [2, ["full", "full"]],
    [3, ["full", "thumb", "thumb"]],
  ])("shows the full photo in the big tiles of %i proofs", (count, shown) => {
    const pictures = proofs(count).map((p) => ({ ...p, src: "thumb", full: "full" }));
    const { container } = render(<ProofMosaic proofs={pictures} onOpen={() => {}} />);
    expect([...container.querySelectorAll("img")].map((img) => img.getAttribute("src"))).toEqual(
      shown,
    );
  });

  it("renders nothing without proofs", () => {
    const { container } = render(<ProofMosaic proofs={[]} />);
    expect(container).toBeEmptyDOMElement();
  });
});

describe("ProofTile", () => {
  it("shows a ready video's length, not while it is prepared", () => {
    const { rerender } = render(
      <ProofTile kind="video" src="/v.jpg" duration="0:42" label="Video" />,
    );
    expect(screen.getByText("0:42")).toBeInTheDocument();
    rerender(<ProofTile kind="video" state="processing" duration="0:42" label="Video" />);
    expect(screen.queryByText("0:42")).not.toBeInTheDocument();
  });
});

describe("MiniWeek", () => {
  it("is one image with a bar per day", () => {
    render(
      <MiniWeek
        label="Last 7 days"
        days={(["done", "missed", "todo", "not_due", "outside", "done", "todo"] as const).map(
          (state, i) => ({ key: String(i), state, today: i === 6 }),
        )}
      />,
    );
    expect(screen.getByRole("img", { name: "Last 7 days" }).children).toHaveLength(7);
  });
});

describe("DayDivider, StatGroup, ChallengeChip", () => {
  it("name the day, the numbers and the challenge", () => {
    render(
      <>
        <DayDivider title="Today" summary="5 check-ins" />
        <StatGroup
          stats={[
            { key: "a", value: "12", label: "days in a row", tone: "success" },
            { key: "b", value: "86%", label: "this month" },
          ]}
        />
        <ChallengeChip icon="book" label="Read" />
      </>,
    );
    expect(screen.getByRole("heading", { name: "Today" })).toBeInTheDocument();
    expect(screen.getByText("5 check-ins")).toBeInTheDocument();
    expect(screen.getByText("days in a row")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.getByText("Read")).toBeInTheDocument();
  });
});

describe("FeedCard", () => {
  const ana = { id: "1", name: "Ana", seed: "ana" };

  it("shows proofs as a mosaic, the challenge, and the footer facts", async () => {
    const onOpenProof = vi.fn();
    render(
      <FeedCard
        person={ana}
        ring="done"
        text="Ana checked in"
        challenge={{ icon: "activity", label: "Walk" }}
        time="5 min ago"
        proofs={proofs(5)}
        onOpenProof={onOpenProof}
        moreLabel="2 more proofs"
        week={{
          label: "Last 7 days",
          days: Array.from({ length: 7 }, (_, i) => ({ key: String(i), state: "done" as const })),
        }}
        facts={["7 days in a row", "day 5 of 30"]}
      />,
    );
    expect(screen.getByRole("article")).toHaveTextContent("Ana checked in");
    expect(screen.getByText("Walk")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Last 7 days" })).toBeInTheDocument();
    expect(screen.getByText("day 5 of 30")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "2 more proofs" }));
    expect(onOpenProof).toHaveBeenLastCalledWith(3);
  });

  it("shows an amount with a bar to the target", () => {
    render(
      <FeedCard
        person={ana}
        text="Ana read"
        amount={{
          value: "+12 pages",
          detail: "20 today",
          progress: { value: 20, max: 30, label: "20 of 30 pages" },
        }}
      />,
    );
    expect(screen.getByText("+12 pages")).toBeInTheDocument();
    expect(screen.getByRole("progressbar", { name: "20 of 30 pages" })).toBeInTheDocument();
  });

  it("has one stage for a flying reaction: the photos, over an amount", () => {
    const amount = { value: "+12 pages", progress: { value: 20, max: 30, label: "20 of 30" } };
    const { container } = render(
      <FeedCard person={ana} text="Ana read" amount={amount} proofs={proofs(1)} />,
    );
    const stages = container.querySelectorAll("[data-stage]");
    expect(stages).toHaveLength(1);
    expect(stages[0]).not.toContainElement(screen.getByRole("progressbar"));
  });

  it("shows a milestone's number and a group's avatars", () => {
    render(
      <>
        <FeedCard
          person={ana}
          tone="success"
          text="Ana"
          highlight={{ value: "7", text: "days in a row" }}
        />
        <FeedCard
          people={{ members: [ana, { id: "2", name: "Dan", seed: "dan" }], label: "Ana and Dan" }}
          text="Ana and Dan checked in Walk"
        />
      </>,
    );
    expect(screen.getByText("7")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Ana and Dan" })).toBeInTheDocument();
  });
});
