import { QueryClient } from "@tanstack/react-query";

import { isApiError } from "@/api";

/** Retry only what can succeed on retry: network failures and server errors, twice. */
export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: (count, error) =>
          count < 2 && (!isApiError(error) || error.status === 0 || error.status >= 500),
        refetchOnWindowFocus: true,
      },
      mutations: { retry: false },
    },
  });
}
