import { useId, type ComponentProps } from "react";

import { cx } from "@/shared/lib/cx";

import styles from "./TextField.module.css";

/** A labelled multi-line field (rules, notes): same look and states as TextField. */
export function TextArea({
  label,
  hint,
  error,
  id,
  className,
  rows = 3,
  ...rest
}: ComponentProps<"textarea"> & { label: string; hint?: string; error?: string }) {
  const generated = useId();
  const fieldId = id ?? generated;
  const describedBy = error ? `${fieldId}-error` : hint ? `${fieldId}-hint` : undefined;
  return (
    <div className={cx(styles.field, className)}>
      <label className={styles.label} htmlFor={fieldId}>
        {label}
      </label>
      <textarea
        id={fieldId}
        rows={rows}
        className={cx(styles.input, styles.multiline, error && styles.invalid)}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy}
        {...rest}
      />
      {error ? (
        <p id={`${fieldId}-error`} className={styles.error} role="alert">
          {error}
        </p>
      ) : (
        hint && (
          <p id={`${fieldId}-hint`} className={styles.hint}>
            {hint}
          </p>
        )
      )}
    </div>
  );
}
