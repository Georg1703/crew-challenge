import { useId, useState, type ComponentProps } from "react";

import { cx } from "@/shared/lib/cx";

import { Icon } from "./Icon";
import styles from "./TextField.module.css";

export interface TextFieldProps extends ComponentProps<"input"> {
  label: string;
  hint?: string;
  error?: string;
  /** On a password field: the label of an eye button that shows what is typed ("Show password"). */
  reveal?: string;
}

export function TextField({
  label,
  hint,
  error,
  reveal,
  id,
  type,
  className,
  ...rest
}: TextFieldProps) {
  const generated = useId();
  const [shown, setShown] = useState(false);
  const inputId = id ?? generated;
  const describedBy = error ? `${inputId}-error` : hint ? `${inputId}-hint` : undefined;
  const input = (
    <input
      id={inputId}
      type={reveal && shown ? "text" : type}
      className={cx(styles.input, error && styles.invalid)}
      aria-invalid={error ? true : undefined}
      aria-describedby={describedBy}
      {...rest}
    />
  );
  return (
    <div className={cx(styles.field, className)}>
      <label className={styles.label} htmlFor={inputId}>
        {label}
      </label>
      {reveal ? (
        <div className={styles.revealable}>
          {input}
          <button
            type="button"
            className={styles.reveal}
            aria-label={reveal}
            aria-pressed={shown}
            onClick={() => setShown((now) => !now)}
          >
            <Icon name={shown ? "eyeOff" : "eye"} size={20} />
          </button>
        </div>
      ) : (
        input
      )}
      {error ? (
        <p id={`${inputId}-error`} className={styles.error} role="alert">
          {error}
        </p>
      ) : (
        hint && (
          <p id={`${inputId}-hint`} className={styles.hint}>
            {hint}
          </p>
        )
      )}
    </div>
  );
}
