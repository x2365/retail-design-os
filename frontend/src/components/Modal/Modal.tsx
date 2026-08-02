import type { ReactNode } from "react";

import styles from "./Modal.module.css";

interface ModalProps {
  title: string;
  sub?: ReactNode;
  onClose: () => void;
  headerExtra?: ReactNode;
  children: ReactNode;
}

export function Modal({ title, sub, onClose, headerExtra, children }: ModalProps) {
  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <div>
            <div className={styles.title}>{title}</div>
            {sub && <div className={styles.sub}>{sub}</div>}
          </div>
          {headerExtra}
          <button className={styles.close} onClick={onClose} title="Закрыть">
            ✕
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
