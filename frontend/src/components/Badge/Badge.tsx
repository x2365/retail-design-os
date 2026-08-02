import type { ReactNode } from "react";

import styles from "./Badge.module.css";

type BadgeColor = "blue" | "green" | "amber" | "red" | "gray";

export function Badge({ color, children }: { color: BadgeColor; children: ReactNode }) {
  return <span className={[styles.badge, styles[color]].join(" ")}>{children}</span>;
}
