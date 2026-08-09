/** Re-exports the shared STAGE_BANDS (see frontend/src/lib/stages.ts, which
 * mirrors backend/app/routers/tasks.py STAGE_BANDS) — the Kanban board's
 * ?band= filter and the backend must agree on the same groups. */
import { type BandKey, STAGE_BANDS } from "../../lib/stages";

export { STAGE_BANDS, type BandKey };

export const KANBAN_COLUMNS: { key: BandKey; title: string; color: string }[] = [
  { key: "dev", title: "ТЗ & Эскиз", color: "#5b6af0" },
  { key: "approval", title: "Согласования & КП", color: "#f59e0b" },
  { key: "production", title: "Образец", color: "#8b5cf6" },
  { key: "logistics", title: "Отгрузка & Финал", color: "#06d6a0" },
];
