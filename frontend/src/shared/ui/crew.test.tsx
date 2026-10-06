import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it, vi } from "vitest";

import { ChallengeChip } from "./ChallengeChip";
import { DayDivider } from "./DayDivider";
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
