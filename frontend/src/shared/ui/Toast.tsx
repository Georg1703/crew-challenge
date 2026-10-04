import { createContext, use, useCallback, useMemo, useRef, useState, type ReactNode } from "react";

import { cx } from "@/shared/lib/cx";
import { AnimatePresence, motion, useSpring } from "@/shared/motion";

import styles from "./Toast.module.css";

type Tone = "info" | "success" | "error";
interface ToastItem {
  id: number;
  tone: Tone;
  message: string;
}
type Show = (message: string, tone?: Tone) => void;

const ToastContext = createContext<Show | null>(null);
const DURATION_MS = 3500;

/** Wrap the app once; call useToast()(message, tone) anywhere below it. */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const nextId = useRef(1);
  const spring = useSpring("snappy");

  const show = useCallback<Show>((message, tone = "info") => {
    const id = nextId.current++;
    setItems((current) => [...current.slice(-2), { id, tone, message }]);
    window.setTimeout(() => setItems((current) => current.filter((t) => t.id !== id)), DURATION_MS);
  }, []);
  const value = useMemo(() => show, [show]);

  return (
    <ToastContext value={value}>
      {children}
      <div className={styles.region} aria-live="polite">
        <AnimatePresence>
          {items.map((item) => (
            <motion.div
              key={item.id}
              layout
              className={cx(styles.toast, styles[item.tone])}
              role={item.tone === "error" ? "alert" : "status"}
              initial={{ opacity: 0, y: -16, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={spring}
            >
              {item.message}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </ToastContext>
  );
}

export function useToast(): Show {
  const show = use(ToastContext);
  if (!show) throw new Error("useToast() needs <ToastProvider> above it.");
  return show;
}
