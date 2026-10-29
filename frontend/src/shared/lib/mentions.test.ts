import { describe, expect, it } from "vitest";

import { findMentions, insertMention, mentionQuery } from "./mentions";

const ana = { id: "a", display_name: "Ana" };
const anaMaria = { id: "am", display_name: "Ana Maria" };
const dan = { id: "d", display_name: "Dan-Ion 2" };
const people = [ana, anaMaria, dan];

describe("findMentions", () => {
  it.each([
    ["@Ana vezi", [{ text: "@Ana", member: ana }, { text: " vezi" }]],
    ["bravo @ana!", [{ text: "bravo " }, { text: "@ana", member: ana }, { text: "!" }]],
    ["@Ana Maria vezi", [{ text: "@Ana Maria", member: anaMaria }, { text: " vezi" }]],
    ["@Anastasia", [{ text: "@Anastasia" }]],
    ["@dan-ion 2 si @Dan", [{ text: "@dan-ion 2", member: dan }, { text: " si @Dan" }]],
    ["ana@example.com @ nimeni", [{ text: "ana@example.com @ nimeni" }]],
    ["@All, @allison", [{ text: "@All", all: true }, { text: ", @allison" }]],
    ["", []],
  ])("splits %j", (text, expected) => {
    expect(findMentions(text, people)).toEqual(expected);
  });
});

describe("mentionQuery", () => {
  it("is the @ under the caret and what follows it", () => {
    expect(mentionQuery("hi @An", 6)).toEqual({ start: 3, query: "An" });
    expect(mentionQuery("@", 1)).toEqual({ start: 0, query: "" });
    expect(mentionQuery("@Ana Ma", 7)).toEqual({ start: 0, query: "Ana Ma" });
    expect(mentionQuery("hi @An", 3)).toBeNull(); // caret before it
    expect(mentionQuery("ana@ex", 6)).toBeNull(); // an email
    expect(mentionQuery("@An\nx", 5)).toBeNull(); // another line
  });
});

describe("insertMention", () => {
  it("replaces what was typed after the @ and leaves the caret after the space", () => {
    expect(insertMention("hi @An there", 3, 6, "Ana")).toEqual({
      value: "hi @Ana  there",
      caret: 8,
    });
  });
});
