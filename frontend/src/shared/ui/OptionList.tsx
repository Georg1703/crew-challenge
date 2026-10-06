import { useId, type ReactNode } from "react";

import { cx } from "@/shared/lib/cx";

import styles from "./OptionList.module.css";

export interface Option<T extends string> {
  value: T;
  title: string;
  description?: string;
  icon?: ReactNode;
}

/** One choice among a few, each explained in a line: "Every day", "Chosen days", ... */
export function OptionList<T extends string>({
  label,
  options,
  value,
  onChange,
  columns = 1,
}: {
  label: string;
  options: Option<T>[];
  value: T;
  onChange: (value: T) => void;
  columns?: 1 | 2;
}) {
  const name = useId();
  return (
    <fieldset className={styles.group}>
      <legend className={styles.legend}>{label}</legend>
      <div className={cx(styles.options, columns === 2 && styles.twoColumns)}>
        {options.map((option) => {
          const selected = option.value === value;
          return (
            <label key={option.value} className={cx(styles.option, selected && styles.selected)}>
              <input
                type="radio"
                className={styles.input}
                name={name}
                value={option.value}
                checked={selected}
                onChange={() => onChange(option.value)}
              />
              {option.icon && <span className={styles.icon}>{option.icon}</span>}
              <span className={styles.text}>
                <span className={styles.title}>{option.title}</span>
                {option.description && (
                  <span className={styles.description}>{option.description}</span>
                )}
              </span>
              <span className={styles.radio} aria-hidden="true" />
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}
