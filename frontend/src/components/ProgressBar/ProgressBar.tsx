import styles from "./ProgressBar.module.css";

type FillColor = "blue" | "green" | "amber" | "red";

export function ProgressBar({ pct, color }: { pct: number; color: FillColor }) {
  const clamped = Math.max(0, Math.min(100, pct));
  return (
    <div className={styles.wrap}>
      <div className={[styles.fill, styles[color]].join(" ")} style={{ width: `${clamped}%` }} />
    </div>
  );
}
