import { useEffect, useState, type CSSProperties } from "react";

interface NumberInputProps {
  value: number;
  onChange: (value: number) => void;
  className?: string;
  style?: CSSProperties;
  min?: number;
  disabled?: boolean;
}

/** Controlled number input that doesn't fight the user while they're
 * clearing/retyping a value.
 *
 * A plain `<input type="number" value={n} onChange={(e) =>
 * setN(Number(e.target.value))}>` looks fine until the user selects-all and
 * deletes to type a fresh number: `Number("")` is `0`, so the field
 * re-renders as "0" the instant it's empty, cursor after it — the next
 * digit then appends instead of replacing ("0" + "5" = "05"). Same failure
 * as the leading-zero bug this fixed for the focus case (`onFocus` ->
 * select-all), just reachable via clear-then-type instead of tab-in-and-type.
 *
 * Fix: keep the field's own text as local state so it can legitimately be
 * empty mid-edit; only reconcile to a real number (0 if left empty) via
 * onBlur, and only push onChange for keystrokes that already parse. */
export function NumberInput({
  value,
  onChange,
  className,
  style,
  min,
  disabled,
}: NumberInputProps) {
  const [text, setText] = useState(String(value));

  // Follow external changes (e.g. task reloads) as long as the user isn't
  // mid-edit with a value that already matches what they'd see anyway.
  useEffect(() => {
    setText((current) => (Number(current) === value ? current : String(value)));
  }, [value]);

  return (
    <input
      type="number"
      className={className}
      style={style}
      min={min}
      disabled={disabled}
      value={text}
      onFocus={(e) => e.target.select()}
      onChange={(e) => {
        const raw = e.target.value;
        setText(raw);
        const n = Number(raw);
        if (raw !== "" && !Number.isNaN(n)) onChange(n);
      }}
      onBlur={() => {
        if (text === "" || Number.isNaN(Number(text))) {
          setText("0");
          onChange(0);
        }
      }}
    />
  );
}
