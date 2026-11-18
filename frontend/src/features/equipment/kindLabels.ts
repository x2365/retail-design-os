import { t } from "../../i18n";
/** Mirrors KIND_LABELS in backend/app/routers/equipment.py. */
export const KIND_LABELS: Record<string, string> = {
  display: t("Дисплей"),
  stand: t("Подставка"),
  corner: t("Корнер"),
  shelf: t("Полка"),
  container: t("Ёмкость"),
  other: t("Прочее"),
};

export const KIND_OPTIONS = Object.entries(KIND_LABELS).map(([value, label]) => ({ value, label }));
