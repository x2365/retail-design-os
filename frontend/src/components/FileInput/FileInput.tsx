import type { ChangeEvent } from "react";

import buttonStyles from "../Button/Button.module.css";
import styles from "./FileInput.module.css";

/** Native `<input type="file">` can't be restyled directly (no border,
 * background, radius control across browsers) — its default rendering is
 * the OS/browser-chrome "Choose file" button, always in the system locale
 * regardless of the page's own language. A hidden input + a real, styled
 * label standing in for it is the standard workaround; the label's native
 * association with the input means it stays keyboard/screen-reader
 * accessible without any click()-forwarding JS. */
export function FileInput({
  onChange,
  disabled,
  label = "Выбрать файл",
}: {
  onChange: (e: ChangeEvent<HTMLInputElement>) => void;
  disabled?: boolean;
  label?: string;
}) {
  return (
    <label
      className={[
        buttonStyles.btn,
        buttonStyles.ghost,
        styles.wrap,
        disabled ? styles.disabled : "",
      ].join(" ")}
    >
      {label}
      <input
        type="file"
        className={styles.hiddenInput}
        onChange={onChange}
        disabled={disabled}
      />
    </label>
  );
}
