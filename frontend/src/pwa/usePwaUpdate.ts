import { useRegisterSW } from "virtual:pwa-register/react";

const CHECK_EVERY_MS = 60 * 60 * 1000;

/**
 * Registers the service worker and reports when a new version is waiting.
 * Checks for updates hourly and whenever the app comes back to the foreground (phones keep
 * installed apps alive for days).
 */
export function usePwaUpdate() {
  const {
    needRefresh: [needRefresh, setNeedRefresh],
    updateServiceWorker,
  } = useRegisterSW({
    onRegisteredSW(_url, registration) {
      if (!registration) return;
      const check = () => void registration.update().catch(() => undefined);
      window.setInterval(check, CHECK_EVERY_MS);
      document.addEventListener("visibilitychange", () => {
        if (document.visibilityState === "visible") check();
      });
    },
  });

  return {
    needRefresh,
    update: () => updateServiceWorker(true),
    later: () => setNeedRefresh(false),
  };
}
