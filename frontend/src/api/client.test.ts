import { afterEach, describe, expect, it, vi } from "vitest";

import { api, call, onUnauthorized } from "./client";
import { ApiError, NETWORK_ERROR } from "./errors";

function respond(status: number, body?: unknown) {
  return new Response(body === undefined ? null : JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("api client", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("sends the CSRF token on unsafe requests, fetching the cookie first", async () => {
    const seen: Request[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: Request | string) => {
        if (typeof input === "string") {
          document.cookie = "csrftoken=abc123; path=/";
          return respond(200, { csrf_token: "abc123" });
        }
        seen.push(input);
        return new Response(null, { status: 204 });
      }),
    );

    await call(api.POST("/api/v1/auth/login", { body: { username: "ana", password: "x" } }));

    expect(seen[0]?.headers.get("X-CSRFToken")).toBe("abc123");
  });

  it("does not send a CSRF token on GET", async () => {
    const seen: Request[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: Request) => {
        seen.push(input);
        return respond(200, { user: {}, member: null, crew: null });
      }),
    );
    await call(api.GET("/api/v1/me"));
    expect(seen[0]?.headers.has("X-CSRFToken")).toBe(false);
  });

  it("turns error responses into ApiError with code and fields", async () => {
    document.cookie = "csrftoken=t; path=/";
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        respond(400, {
          error: { code: "username_taken", message: "Taken.", fields: { username: ["Taken."] } },
        }),
      ),
    );
    const error = await call(
      api.POST("/api/v1/invites/{code}/accept", {
        params: { path: { code: "c" } },
        body: { username: "a", password: "b", display_name: "c" },
      }),
    ).catch((e: unknown) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).code).toBe("username_taken");
    expect((error as ApiError).field("username")).toBe("Taken.");
  });

  it("reports network failures with their own code", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => Promise.reject(new TypeError("offline"))),
    );
    const error = (await call(api.GET("/api/v1/crew")).catch((e: unknown) => e)) as ApiError;
    expect(error.code).toBe(NETWORK_ERROR);
    expect(error.status).toBe(0);
  });

  it("notifies listeners on 401, except for the session probe GET /me", async () => {
    const listener = vi.fn();
    const stop = onUnauthorized(listener);
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => respond(401, { error: { code: "not_authenticated" } })),
    );

    await call(api.GET("/api/v1/me")).catch(() => undefined);
    expect(listener).not.toHaveBeenCalled();

    await call(api.GET("/api/v1/crew")).catch(() => undefined);
    expect(listener).toHaveBeenCalledTimes(1);
    stop();
  });
});
