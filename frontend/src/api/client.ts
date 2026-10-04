/**
 * The typed API client. The only module that talks to the network (ESLint enforces it).
 *
 * - Types come from schema.gen.ts, generated from contracts/openapi.yaml by `make schema`.
 * - Unsafe requests carry the CSRF token; the cookie is fetched first if missing.
 * - Every non-2xx response becomes an ApiError; a 401 also notifies the app (session gone).
 */
import createClient, { type Middleware } from "openapi-fetch";

import { ensureCsrfCookie, UNSAFE_METHODS } from "./csrf";
import { ApiError, NETWORK_ERROR, type ApiErrorBody } from "./errors";
import type { paths } from "./schema.gen";

type Listener = () => void;
const unauthorizedListeners = new Set<Listener>();

/** Called on any 401 except the session probe (GET /me). Returns an unsubscribe function. */
export function onUnauthorized(listener: Listener): () => void {
  unauthorizedListeners.add(listener);
  return () => unauthorizedListeners.delete(listener);
}

const csrf: Middleware = {
  async onRequest({ request }) {
    if (UNSAFE_METHODS.has(request.method)) {
      request.headers.set("X-CSRFToken", await ensureCsrfCookie());
    }
    return request;
  },
  onResponse({ response, request }) {
    if (response.status === 401 && !request.url.endsWith("/api/v1/me")) {
      unauthorizedListeners.forEach((listener) => listener());
    }
    return response;
  },
};

export const api = createClient<paths>({
  // Absolute base: same origin as the page (Vite or Caddy forwards /api to Django).
  baseUrl: globalThis.location.origin,
  credentials: "same-origin",
  // Look fetch up at call time (not at import), so tests and polyfills can replace it.
  fetch: (request) => globalThis.fetch(request),
});
api.use(csrf);

interface FetchResult<T> {
  data?: T;
  error?: unknown;
  response: Response;
}

/** Return the data of a successful call, or throw an ApiError. */
export async function call<T>(request: Promise<FetchResult<T>>): Promise<T> {
  let result: FetchResult<T>;
  try {
    result = await request;
  } catch {
    throw new ApiError(0, { code: NETWORK_ERROR, message: "Network error." });
  }
  const { data, error, response } = result;
  if (!response.ok) {
    const body = (error as { error?: ApiErrorBody } | undefined)?.error;
    throw new ApiError(response.status, body);
  }
  return data as T;
}
