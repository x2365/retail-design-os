/** Mirrors KIND_LABELS in backend/app/routers/equipment.py. */
export const KIND_LABELS: Record<string, string> = {
  display: "Дисплей",
  stand: "Подставка",
  corner: "Корнер",
  shelf: "Полка",
  container: "Ёмкость",
  other: "Прочее",
};

export const KIND_OPTIONS = Object.entries(KIND_LABELS).map(([value, label]) => ({ value, label }));
