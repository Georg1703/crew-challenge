import { createContext, use, useCallback, useMemo, useRef, useState, type ReactNode } from "react";

import { cx } from "@/shared/lib/cx";
import { AnimatePresence, motion, useSpring } from "@/shared/motion";

import { Icon } from "./Icon";
import styles from "./Toast.module.css";

type Tone = "info" | "success" | "error";
/** One short action in the toast, for example "Undo". */
interface ToastAction {
  label: string;
  onClick: () => void;
}
interface ToastItem {
  id: number;
  tone: Tone;
  message: string;
  action?: ToastAction;
}
type Show = (message: string, tone?: Tone, action?: ToastAction) => void;

const ToastContext = createContext<Show | null>(null);
const DURATION_MS = 3500;
const WITH_ACTION_MS = 5000; // long enough to reach "Undo"

/** Wrap the app once; call useToast()(message, tone, action?) anywhere below it. */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const nextId = useRef(1);
  const spring = useSpring("snappy");

  const dismiss = useCallback(
    (id: number) => setItems((current) => current.filter((t) => t.id !== id)),
    [],
  );
  const show = useCallback<Show>(
    (message, tone = "info", action) => {
      const id = nextId.current++;
      setItems((current) => [...current.slice(-2), { id, tone, message, action }]);
      window.setTimeout(() => dismiss(id), action ? WITH_ACTION_MS : DURATION_MS);
    },
    [dismiss],
  );
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
              initial={{ opacity: 0, y: 16, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={spring}
            >
              <span className={styles.mark} aria-hidden="true">
                <Icon name={item.tone === "error" ? "alert" : "check"} size={16} />
              </span>
              {item.message}
              {item.action && (
                <button
                  type="button"
                  className={styles.action}
                  onClick={() => {
                    item.action?.onClick();
                    dismiss(item.id);
                  }}
                >
                  {item.action.label}
                </button>
              )}
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
