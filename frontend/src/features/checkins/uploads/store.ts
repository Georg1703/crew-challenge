/**
 * Uploads in flight, kept outside the screens so they run while the person uses the app. Only
 * this session's uploads live here; finished ones come back from the API as the card's proofs.
 */
import { create } from "zustand";

export type UploadState = "uploading" | "paused" | "failed";

export interface LocalUpload {
  /** Uppy's file id. */
  id: string;
  proofId: string;
  challengeId: string;
  kind: "photo" | "video";
  /** Object URL of the thumbnail (or the shrunk photo) shown on the tile. */
  preview: string | null;
  state: UploadState;
  /** 0 to 1. */
  progress: number;
  size: number;
}

interface Uploads {
  items: Record<string, LocalUpload>;
  put: (upload: LocalUpload) => void;
  patch: (id: string, change: Partial<LocalUpload>) => void;
  drop: (id: string) => void;
}

export const useUploads = create<Uploads>()((set) => ({
  items: {},
  put: (upload) => set((s) => ({ items: { ...s.items, [upload.id]: upload } })),
  patch: (id, change) =>
    set((s) => {
      const item = s.items[id];
      return item ? { items: { ...s.items, [id]: { ...item, ...change } } } : s;
    }),
  drop: (id) =>
    set((s) => {
      const { [id]: gone, ...items } = s.items;
      if (gone?.preview) URL.revokeObjectURL(gone.preview);
      return { items };
    }),
}));

/** For the tab bar: how many uploads run and how far they are, by bytes (0 to 1). */
export function summary(items: Record<string, LocalUpload>): { count: number; progress: number } {
  const running = Object.values(items).filter((u) => u.state !== "failed");
  const total = running.reduce((sum, u) => sum + u.size, 0);
  const sent = running.reduce((sum, u) => sum + u.size * u.progress, 0);
  return { count: running.length, progress: total ? sent / total : 0 };
}
