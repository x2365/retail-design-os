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
    label: "Обзор",
    items: [
      { to: "/", icon: "◈", label: "Дашборд" },
      { to: "/pipeline", icon: "⬡", label: "Воронка задач" },
      { to: "/gantt", icon: "▤", label: "Таймлайн" },
      { to: "/archive", icon: "🗄", label: "Архив задач" },
    ],
  },
  {
    label: "Финансы",
    items: [
      { to: "/budget", icon: "◎", label: "Бюджеты" },
      { to: "/payments", icon: "◇", label: "Оплаты / КП" },
    ],
  },
  {
    label: "Логистика",
    items: [{ to: "/tt", icon: "◉", label: "Торговые точки" }],
  },
  {
    label: "Система",
    items: [
      { to: "/approvals", icon: "✓", label: "Согласования" },
      { to: "/brands", icon: "◈", label: "Бренды" },
      { to: "/library", icon: "▦", label: "Библиотека" },
      { to: "/users", icon: "👤", label: "Пользователи", adminOnly: true },
    ],
  },
];

export const ROUTE_TITLES: Record<string, string> = {
  "/": "Дашборд",
  "/pipeline": "Воронка задач",
  "/gantt": "Таймлайн",
  "/archive": "Архив задач",
  "/budget": "Бюджеты",
  "/payments": "Оплаты / КП",
  "/tt": "Торговые точки",
  "/approvals": "Согласования",
  "/brands": "Бренды",
  "/library": "Библиотека",
  "/users": "Пользователи",
};
