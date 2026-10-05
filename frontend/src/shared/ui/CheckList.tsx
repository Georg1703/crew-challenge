import type { ReactNode } from "react";

import { cx } from "@/shared/lib/cx";

import styles from "./CheckList.module.css";
import { Icon } from "./Icon";

export type CheckOption<T> = {
  value: T;
  title: string;
  description?: string;
  /** For example an `Avatar`. */
  leading?: ReactNode;
  /** Shown checked or unchecked but cannot be changed (for example the creator). */
  disabled?: boolean;
};

/** Several rows to pick from, each with a check box (who takes part). */
export function CheckList<T extends string>({
  label,
  options,
  values,
  onChange,
  error,
}: {
  label: string;
  options: CheckOption<T>[];
  values: T[];
  onChange: (values: T[]) => void;
  error?: string;
}) {
  const toggle = (value: T) =>
    onChange(values.includes(value) ? values.filter((v) => v !== value) : [...values, value]);
  return (
    <fieldset className={styles.group} aria-invalid={error ? true : undefined}>
      <legend className={styles.legend}>{label}</legend>
      <div className={styles.rows}>
        {options.map((option) => {
          const on = values.includes(option.value);
          return (
            <label
              key={option.value}
              className={cx(styles.row, on && styles.on, option.disabled && styles.disabled)}
            >
              <input
                type="checkbox"
                className={styles.input}
                checked={on}
                disabled={option.disabled}
                onChange={() => toggle(option.value)}
              />
              {option.leading}
              <span className={styles.text}>
                <span className={styles.title}>{option.title}</span>
                {option.description && (
                  <span className={styles.description}>{option.description}</span>
                )}
              </span>
              <span className={styles.box} aria-hidden="true">
                {on && <Icon name="check" size={16} />}
              </span>
            </label>
          );
        })}
      </div>
      {error && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}
    </fieldset>
  );
}
