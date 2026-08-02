import type { ReactNode } from "react";

import styles from "./KpiCard.module.css";

type Accent = "blue" | "green" | "amber" | "red" | "purple";

interface KpiCardProps {
  accent: Accent;
  label: string;
  value: ReactNode;
  valueColor?: string;
  valueFontSize?: number;
  sub?: ReactNode;
  delta?: ReactNode;
  deltaDirection?: "up" | "down";
}

export function KpiCard({
  accent,
  label,
  value,
  valueColor,
  valueFontSize,
  sub,
  delta,
  deltaDirection,
}: KpiCardProps) {
  return (
    <div className={[styles.card, styles[accent]].join(" ")}>
      <div className={styles.label}>{label}</div>
      <div
        className={styles.value}
        style={{
          ...(valueColor ? { color: valueColor } : undefined),
          ...(valueFontSize ? { fontSize: valueFontSize } : undefined),
        }}
      >
        {value}
      </div>
      {sub !== undefined && <div className={styles.sub}>{sub}</div>}
      {delta !== undefined && (
        <div className={[styles.delta, deltaDirection ? styles[deltaDirection] : ""].join(" ")}>
          {delta}
        </div>
      )}
    </div>
  );
}

export function KpiRow({ children }: { children: ReactNode }) {
  return <div className={styles.row}>{children}</div>;
}
