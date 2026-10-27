import { useEffect, useState } from "react";

import { detectPlatform } from "@/pwa";

import { usePushKey, useSubscribePush, useUnsubscribePush } from "./api";
import {
  currentSubscription,
  pushPermission,
  pushSupported,
  subscribePush,
  unsubscribePush,
} from "./push";

/**
 * Where push stands on this device: `unavailable` (the browser cannot, or the server has no
 * key), `install` (an iPhone in Safari: only the installed app can), `denied` (blocked in the
 * browser), `off`, `on`; `unknown` while it is being worked out.
 */
export type PushState = "unknown" | "unavailable" | "install" | "denied" | "off" | "on";

export function usePush() {
  const [platform] = useState(detectPlatform);
  const supported = pushSupported() && !(platform.ios && !platform.standalone);
  const key = usePushKey(supported);
  const subscribe = useSubscribePush();
  const unsubscribe = useUnsubscribePush();
  const [subscribed, setSubscribed] = useState<boolean | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!supported) return;
    let live = true;
    void currentSubscription().then((current) => live && setSubscribed(current !== null));
    return () => {
      live = false;
    };
  }, [supported]);

  const state: PushState = !pushSupported()
    ? "unavailable"
    : platform.ios && !platform.standalone
      ? "install"
      : key.isPending || subscribed === null
        ? "unknown"
        : !key.data
          ? "unavailable"
          : pushPermission() === "denied"
            ? "denied"
            : subscribed
              ? "on"
              : "off";

  const enable = async () => {
    setFailed(false);
    try {
      const subscription = key.data ? await subscribePush(key.data) : null;
      if (!subscription) return setFailed(pushPermission() !== "denied");
      await subscribe.mutateAsync(subscription);
      setSubscribed(true);
    } catch {
      setFailed(true);
    }
  };

  const disable = async () => {
    setFailed(false);
    try {
      const endpoint = await unsubscribePush();
      if (endpoint) await unsubscribe.mutateAsync(endpoint);
      setSubscribed(false);
    } catch {
      setFailed(true);
    }
  };

  return {
    state,
    failed,
    busy: subscribe.isPending || unsubscribe.isPending,
    enable,
    disable,
  };
}
