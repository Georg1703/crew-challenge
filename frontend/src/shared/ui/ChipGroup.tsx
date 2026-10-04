import { cx } from "@/shared/lib/cx";

import styles from "./ChipGroup.module.css";

/** Several short choices that can be combined, as round chips (days of the week, quick ideas). */
export function ChipGroup<T extends string | number>({
  label,
  options,
  values,
  onChange,
  error,
}: {
  label: string;
  options: { value: T; label: string; name?: string }[];
  values: T[];
  onChange: (values: T[]) => void;
  error?: string;
}) {
  const toggle = (value: T) =>
    onChange(values.includes(value) ? values.filter((v) => v !== value) : [...values, value]);
  return (
    <fieldset className={styles.group} aria-invalid={error ? true : undefined}>
      <legend className={styles.legend}>{label}</legend>
      <div className={styles.chips}>
        {options.map((option) => {
          const on = values.includes(option.value);
          return (
            <label key={String(option.value)} className={cx(styles.chip, on && styles.on)}>
              <input
                type="checkbox"
                className={styles.input}
                checked={on}
                onChange={() => toggle(option.value)}
                aria-label={option.name}
              />
              {option.label}
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
