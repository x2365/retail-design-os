import { NavLink } from "react-router-dom";

import { NAV_SECTIONS } from "./navConfig";
import styles from "./MobileNavDrawer.module.css";

interface MobileNavDrawerProps {
  open: boolean;
  onClose: () => void;
  isAdmin: boolean;
}

/** Mobile-only (≤960px) slide-out nav — replaces the icon-only sidebar rail
 * there with a full, labeled menu built from the same NAV_SECTIONS data the
 * desktop sidebar uses (AppShell.tsx). */
export function MobileNavDrawer({ open, onClose, isAdmin }: MobileNavDrawerProps) {
  if (!open) return null;

  return (
    <div className={styles.overlay} onClick={onClose}>
      <aside className={styles.drawer} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <div className={styles.logoMark}>RetailDesign</div>
          <button className={styles.close} onClick={onClose} title="Закрыть">
            ✕
          </button>
        </div>

        {NAV_SECTIONS.map((section) => {
          const items = section.items.filter((item) => !item.adminOnly || isAdmin);
          if (items.length === 0) return null;
          return (
            <div className={styles.navSection} key={section.label}>
              <div className={styles.navLabel}>{section.label}</div>
              {items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === "/"}
                  className={({ isActive }) =>
                    [styles.navItem, isActive ? styles.navItemActive : ""].filter(Boolean).join(" ")
                  }
                  onClick={onClose}
                >
                  <span className={styles.navIcon}>{item.icon}</span>
                  <span className={styles.navText}>{item.label}</span>
                </NavLink>
              ))}
            </div>
          );
        })}
      </aside>
    </div>
  );
}
