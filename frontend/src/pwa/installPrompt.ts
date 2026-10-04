/**
 * Android/desktop Chrome fire `beforeinstallprompt` once, often before React mounts. We capture
 * it at startup (see main.tsx) and keep it here so the install button can use it later.
 */
import { useSyncExternalStore } from "react";

export interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

let deferred: BeforeInstallPromptEvent | null = null;
let installed = false;
const listeners = new Set<() => void>();
const emit = () => listeners.forEach((listener) => listener());

export function captureInstallPrompt(target: Window = window): void {
  target.addEventListener("beforeinstallprompt", (event) => {
    event.preventDefault(); // we show our own button
    deferred = event as BeforeInstallPromptEvent;
    emit();
  });
  target.addEventListener("appinstalled", () => {
    deferred = null;
    installed = true;
    emit();
  });
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/** Whether the browser offers its install dialog, and a function to open it. */
export function useInstallPrompt() {
  const canPrompt = useSyncExternalStore(subscribe, () => deferred !== null);
  const justInstalled = useSyncExternalStore(subscribe, () => installed);
  const prompt = async (): Promise<boolean> => {
    const event = deferred;
    if (!event) return false;
    await event.prompt();
    const { outcome } = await event.userChoice;
    deferred = null;
    emit();
    return outcome === "accepted";
  };
  return { canPrompt, justInstalled, prompt };
}

/** Test helper: forget any captured prompt. */
export function resetInstallPrompt(): void {
  deferred = null;
  installed = false;
  emit();
}
