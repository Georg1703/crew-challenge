import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { createMemoryRouter, RouterProvider, type RouteObject } from "react-router";

import { Providers } from "@/app/providers";
import { createQueryClient } from "@/app/queryClient";

/**
 * Render routes inside the real providers with an in-memory router.
 * Mock the API with vi.spyOn(api, "GET" | "POST" | "PATCH"), never by mocking fetch.
 */
export function renderRoutes(routes: RouteObject[], { at = "/" }: { at?: string } = {}) {
  const client = createQueryClient();
  client.setDefaultOptions({ queries: { retry: false }, mutations: { retry: false } });
  const router = createMemoryRouter(routes, { initialEntries: [at] });
  const result = render(
    <Providers client={client}>
      <RouterProvider router={router} />
    </Providers>,
  );
  return { ...result, router, client };
}

export function renderScreen(element: ReactElement, options: { at?: string; path?: string } = {}) {
  const path = options.path ?? "/";
  return renderRoutes(
    [
      { path, element },
      { path: "*", element: <p>other page</p> },
    ],
    {
      at: options.at ?? path,
    },
  );
}

/** An openapi-fetch style result for spyOn mocks. */
export function ok<T>(data: T, status = 200) {
  return Promise.resolve({ data, error: undefined, response: new Response(null, { status }) });
}

export function fail(
  status: number,
  error: { code: string; message?: string; fields?: Record<string, string[]> },
) {
  return Promise.resolve({
    data: undefined,
    error: { error: { message: error.code, ...error } },
    response: new Response(null, { status }),
  });
}
