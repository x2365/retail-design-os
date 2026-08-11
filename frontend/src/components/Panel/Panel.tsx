import { useState, type ReactNode } from "react";

import styles from "./Panel.module.css";

interface PanelProps {
  title: string;
  leading?: ReactNode;
  count?: number;
  countAlert?: boolean;
  actions?: ReactNode;
  bodyStyle?: React.CSSProperties;
  collapsible?: boolean;
  defaultOpen?: boolean;
  children: ReactNode;
}

export function Panel({
  title,
  leading,
  count,
  countAlert,
  actions,
  bodyStyle,
  collapsible = false,
  defaultOpen = true,
  children,
}: PanelProps) {
  const [open, setOpen] = useState(defaultOpen);
  const isOpen = !collapsible || open;

  return (
    <div className={styles.panel}>
      <div
        className={[styles.header, collapsible ? styles.headerClickable : ""].join(" ")}
        onClick={collapsible ? () => setOpen((o) => !o) : undefined}
        role={collapsible ? "button" : undefined}
        tabIndex={collapsible ? 0 : undefined}
        onKeyDown={
          collapsible
            ? (e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  setOpen((o) => !o);
                }
              }
            : undefined
        }
      >
        {collapsible && (
          <span className={[styles.chevron, isOpen ? styles.chevronOpen : ""].join(" ")}>▸</span>
        )}
        {leading}
        <div className={styles.title}>{title}</div>
        {count !== undefined && (
          <span className={[styles.count, countAlert ? styles.countAlert : ""].join(" ")}>
            {count}
          </span>
        )}
        {actions && (
          <div className={styles.actions} onClick={(e) => e.stopPropagation()}>
            {actions}
          </div>
        )}
      </div>
      {isOpen && (
        <div className={styles.body} style={bodyStyle}>
          {children}
        </div>
      )}
    </div>
  );
}
