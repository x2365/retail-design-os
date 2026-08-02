import { useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { ROLE_LABELS, type Role } from "../auth/roles";
import { useChangeMyPassword } from "../api/queries/users";
import { PasswordModal } from "../features/users/PasswordModal";
import { NAV_SECTIONS, ROUTE_TITLES } from "./navConfig";
import styles from "./AppShell.module.css";

function initials(fullName: string): string {
  const parts = fullName.trim().split(/\s+/).filter(Boolean);
  const letters = parts.slice(0, 2).map((p) => p[0]?.toUpperCase() ?? "");
  return letters.join("") || "?";
}

export default function AppShell() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const title = ROUTE_TITLES[location.pathname] ?? "RetailDesign OS";
  const changeMyPassword = useChangeMyPassword();
  const [changingPassword, setChangingPassword] = useState(false);

  return (
    <div className={styles.app}>
      <aside className={styles.sidebar}>
        <div className={styles.logo}>
          <div className={styles.logoMark}>RetailDesign</div>
          <div className={styles.logoSub}>OS v1.0 · Portfolio</div>
        </div>

        {NAV_SECTIONS.map((section) => {
          const items = section.items.filter((item) => !item.adminOnly || user?.role === "admin");
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
                >
                  <span className={styles.navIcon}>{item.icon}</span>
                  <span>{item.label}</span>
                </NavLink>
              ))}
            </div>
          );
        })}

        {user && (
          <div className={styles.sidebarFooter}>
            <div className={styles.userCard}>
              <div className={styles.userAvatar}>{initials(user.full_name)}</div>
              <div className={styles.userInfo}>
                <div className={styles.userName}>{user.full_name}</div>
                <div className={styles.userRole}>{ROLE_LABELS[user.role as Role] ?? user.role}</div>
              </div>
              <button
                className={styles.navItem}
                style={{ padding: "4px 7px" }}
                title="Сменить пароль"
                onClick={() => setChangingPassword(true)}
              >
                🔑
              </button>
              <button
                className={styles.navItem}
                style={{ padding: "4px 7px" }}
                title="Выйти"
                onClick={logout}
              >
                ⎋
              </button>
            </div>
          </div>
        )}
      </aside>

      {changingPassword && (
        <PasswordModal
          title="Сменить пароль"
          requireCurrent
          onSubmit={({ currentPassword, newPassword }) =>
            changeMyPassword.mutateAsync({ currentPassword: currentPassword ?? "", newPassword })
          }
          onClose={() => setChangingPassword(false)}
        />
      )}

      <div className={styles.main}>
        <div className={styles.topbar}>
          <div className={styles.topbarTitle}>{title}</div>
        </div>
        <div className={styles.content}>
          <Outlet />
        </div>
      </div>
    </div>
  );
}
