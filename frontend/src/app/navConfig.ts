import { t } from "../i18n";
/** Sidebar structure — ported from the old app's <aside class="sidebar"> markup
 * (section labels, icons, order, grouping) so the rewrite keeps the same
 * information architecture. `adminOnly` items are hidden unless the current
 * user's role is "admin" (mirrors CURRENT_USER.role==='admin' in the old app). */
export interface NavItem {
  to: string;
  icon: string;
  label: string;
  adminOnly?: boolean;
}

export interface NavSection {
  label: string;
  items: NavItem[];
}

export const NAV_SECTIONS: NavSection[] = [
  {
    label: t("Обзор"),
    items: [
      { to: "/", icon: "📊", label: t("Дашборд") },
      { to: "/pipeline", icon: "🧩", label: t("Воронка задач") },
      { to: "/metrics", icon: "📉", label: t("Метрики") },
      { to: "/gantt", icon: "⏱️", label: t("Таймлайн") },
      { to: "/archive", icon: "📦", label: t("Архив задач") },
    ],
  },
  {
    label: t("Финансы"),
    items: [
      { to: "/budget", icon: "💵", label: t("Бюджеты") },
      { to: "/payments", icon: "🧾", label: t("Оплаты / КП") },
    ],
  },
  {
    label: t("Логистика"),
    items: [{ to: "/tt", icon: "📍", label: t("Торговые точки") }],
  },
  {
    label: t("Система"),
    items: [
      { to: "/approvals", icon: "☑️", label: t("Согласования") },
      { to: "/brands", icon: "🔖", label: t("Бренды") },
      { to: "/library", icon: "📂", label: t("Библиотека") },
      { to: "/users", icon: "👤", label: t("Пользователи"), adminOnly: true },
    ],
  },
];

export const ROUTE_TITLES: Record<string, string> = {
  "/": t("Дашборд"),
  "/pipeline": t("Воронка задач"),
  "/metrics": t("Метрики"),
  "/gantt": t("Таймлайн"),
  "/archive": t("Архив задач"),
  "/budget": t("Бюджеты"),
  "/payments": t("Оплаты / КП"),
  "/tt": t("Торговые точки"),
  "/approvals": t("Согласования"),
  "/brands": t("Бренды"),
  "/library": t("Библиотека"),
  "/users": t("Пользователи"),
};
