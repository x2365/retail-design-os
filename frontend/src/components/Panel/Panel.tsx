import type { ReactNode } from "react";

import styles from "./Panel.module.css";

interface PanelProps {
  title: string;
  count?: number;
  countAlert?: boolean;
  actions?: ReactNode;
  bodyStyle?: React.CSSProperties;
  children: ReactNode;
}

export function Panel({ title, count, countAlert, actions, bodyStyle, children }: PanelProps) {
  return (
    <div className={styles.panel}>
      <div className={styles.header}>
        <div className={styles.title}>{title}</div>
        {count !== undefined && (
          <span className={[styles.count, countAlert ? styles.countAlert : ""].join(" ")}>
            {count}
          </span>
        )}
        {actions && <div className={styles.actions}>{actions}</div>}
      </div>
      <div className={styles.body} style={bodyStyle}>
        {children}
      </div>
    </div>
  );
}
