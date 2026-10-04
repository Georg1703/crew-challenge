/** Test stand-in for "virtual:pwa-register/react". Tests flip `pwaMock.needRefresh`. */
import { useState } from "react";
import { vi } from "vitest";

export const pwaMock = { needRefresh: false, updateServiceWorker: vi.fn(async () => undefined) };

export function useRegisterSW() {
  const needRefresh = useState(pwaMock.needRefresh);
  const offlineReady = useState(false);
  return { needRefresh, offlineReady, updateServiceWorker: pwaMock.updateServiceWorker };
}
