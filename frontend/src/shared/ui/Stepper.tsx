import { useId } from "react";

import { Icon } from "./Icon";
import styles from "./Stepper.module.css";

/** A small whole number with minus and plus buttons ("3 times a week"). */
export function Stepper({
  label,
  value,
  min,
  max,
  onChange,
  decreaseLabel,
  increaseLabel,
  suffix,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  onChange: (value: number) => void;
  decreaseLabel: string;
  increaseLabel: string;
  suffix?: string;
}) {
  const id = useId();
  const set = (next: number) => onChange(Math.min(max, Math.max(min, next)));
  return (
    <div className={styles.field}>
      <label className={styles.label} htmlFor={id}>
        {label}
      </label>
      <div className={styles.row}>
        <button
          type="button"
          className={styles.button}
          onClick={() => set(value - 1)}
          disabled={value <= min}
          aria-label={decreaseLabel}
        >
          <Icon name="minus" size={20} />
        </button>
        <input
          id={id}
          className={styles.input}
          type="number"
          inputMode="numeric"
          min={min}
          max={max}
          value={value}
          onChange={(event) => set(Number(event.target.value) || min)}
        />
        <button
          type="button"
          className={styles.button}
          onClick={() => set(value + 1)}
          disabled={value >= max}
          aria-label={increaseLabel}
        >
          <Icon name="plus" size={20} />
        </button>
        {suffix && <span className={styles.suffix}>{suffix}</span>}
      </div>
    </div>
  );
}
