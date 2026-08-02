import type { ButtonHTMLAttributes } from "react";

import styles from "./Button.module.css";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "ghost" | "danger";
}

export function Button({ variant = "ghost", className, ...rest }: ButtonProps) {
  const variantClass =
    variant === "primary" ? styles.primary : variant === "danger" ? styles.danger : styles.ghost;
  return (
    <button className={[styles.btn, variantClass, className].filter(Boolean).join(" ")} {...rest} />
  );
}
