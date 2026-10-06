import { useId } from "react";

import { Icon, type IconName } from "./Icon";
import styles from "./IconPicker.module.css";

/** Pick one icon from a small set (the icon of a challenge). Each option needs a name. */
export function IconPicker<T extends string>({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: { value: T; icon: IconName; name: string }[];
  value: T;
  onChange: (value: T) => void;
}) {
  const group = useId();
  return (
    <fieldset className={styles.group}>
      <legend className={styles.legend}>{label}</legend>
      <div className={styles.grid}>
        {options.map((option) => (
          <label key={option.value} className={styles.choice} title={option.name}>
            <input
              type="radio"
              name={group}
              value={option.value}
              checked={option.value === value}
              onChange={() => onChange(option.value)}
              aria-label={option.name}
            />
            <Icon name={option.icon} />
          </label>
        ))}
      </div>
    </fieldset>
  );
}
