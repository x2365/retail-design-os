/** Mirrors backend/app/routers/tasks.py STAGE_BANDS exactly (same keys and
 * stage lists) so the Kanban board's ?band= filter and the backend agree —
 * the old frontend hardcoded a second, slightly different copy of this
 * grouping and never actually used the `band` query param at all. */
export const STAGE_BANDS = {
  dev: [1, 2],
  approval: [3, 4, 5, 6],
  production: [7, 8],
  logistics: [9, 10, 11, 12],
} as const;

export type BandKey = keyof typeof STAGE_BANDS;

export const KANBAN_COLUMNS: { key: BandKey; title: string; color: string }[] = [
  { key: "dev", title: "ТЗ & Эскиз", color: "#5b6af0" },
  { key: "approval", title: "Дизайн & Подготовка", color: "#f59e0b" },
  { key: "production", title: "Отгрузка", color: "#8b5cf6" },
  { key: "logistics", title: "Доставка & Финал", color: "#06d6a0" },
];
