import type { ComponentProps, ReactNode } from "react";

import { cx } from "@/shared/lib/cx";
import { motion, pressScale, useSpring } from "@/shared/motion";

import styles from "./Button.module.css";
import { Spinner } from "./Spinner";

type Variant = "primary" | "secondary" | "ghost" | "danger";

export interface ButtonProps extends Omit<ComponentProps<typeof motion.button>, "children"> {
  variant?: Variant;
  size?: "md" | "lg";
  loading?: boolean;
  fullWidth?: boolean;
  icon?: ReactNode;
  children?: ReactNode;
}

export function Button({
  variant = "primary",
  size = "md",
  loading = false,
  fullWidth = false,
  icon,
  disabled,
  className,
  children,
  type = "button",
  ...rest
}: ButtonProps) {
  const transition = useSpring("snappy");
  const inactive = disabled || loading;
  return (
    <motion.button
      type={type}
      className={cx(
        styles.button,
        styles[variant],
        styles[size],
        fullWidth && styles.fullWidth,
        className,
      )}
      disabled={inactive}
      aria-busy={loading || undefined}
      whileTap={inactive ? undefined : { scale: pressScale }}
      transition={transition}
      {...rest}
    >
      {loading ? <Spinner size="sm" /> : icon}
      {children && <span>{children}</span>}
    </motion.button>
  );
}
