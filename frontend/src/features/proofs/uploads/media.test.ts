import { describe, expect, it } from "vitest";

import { preparePhoto } from "./media";

describe("preparePhoto", () => {
  it("sends a GIF as it is, so it keeps moving", async () => {
    const gif = new File(["GIF89a"], "dance.gif", { type: "image/gif" });
    const prepared = await preparePhoto(gif);
    expect(prepared.body).toBe(gif);
    expect(prepared.contentType).toBe("image/gif");
    expect(prepared.thumb).toBeNull(); // nothing to draw it with here
  });
});
