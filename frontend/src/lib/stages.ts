/** Single source of truth for the 10-stage POSM pipeline — mirrors
 * backend/app/models/enums.py TaskStage exactly (same numeric order, same
 * Russian labels). Every screen rendering stage labels, counts, band
 * groupings or stage colors should derive from here instead of hand-rolling
 * another copy — this repo had 7 independent hardcoded copies before this
 * file existed; don't add an 8th. */

export const STAGE_LABELS: Record<number, string> = {
  1: "ТЗ получено",
  2: "Разработка дизайна",
  3: "Согласования",
  4: "Бюджет и КП",
  5: "Документы",
  6: "Образец и Производство",
  7: "Отгрузка",
  8: "Монтаж",
  9: "Распределение по ТТ",
  10: "Закрыт",
};

// Shorter labels for the task-detail modal's tab strip (10 tabs need to fit
// across one header row).
export const STAGE_TAB_LABELS: Record<number, string> = {
  1: "ТЗ",
  2: "Дизайн",
  3: "Согласования",
  4: "Бюджет и КП",
  5: "Документы",
  6: "Образец",
  7: "Отгрузка",
  8: "Монтаж",
  9: "Распределение",
  10: "Закрыт",
};

export const FIRST_STAGE = 1;
export const LAST_STAGE = 10;
export const TOTAL_STAGES = 10;
export const INSTALL_STAGE = 8; // "Монтаж" — corner-only
export const FINAL_APPROVAL_STAGE = 9; // "Распределение по ТТ"

export function stageLabel(stage: number): string {
  return STAGE_LABELS[stage] ?? String(stage);
}

export function isClosed(stage: number): boolean {
  return stage >= LAST_STAGE;
}

/** Монтаж применяется только к corner-оборудованию. Задачи без привязки к
 * изделию (equipmentKind == null) по умолчанию считаются требующими монтаж —
 * скрываем/пропускаем этап только когда точно знаем, что изделие не corner.
 * Совпадает с бэкендом (task_stage.py::_wants_install). */
export function showsInstallStage(equipmentKind: string | null | undefined): boolean {
  return equipmentKind == null || equipmentKind === "corner";
}

export function nextStageFor(stage: number, equipmentKind: string | null | undefined): number {
  const n = Math.min(stage + 1, LAST_STAGE);
  return n === INSTALL_STAGE && !showsInstallStage(equipmentKind) ? Math.min(n + 1, LAST_STAGE) : n;
}

export function prevStageFor(stage: number, equipmentKind: string | null | undefined): number {
  const p = Math.max(stage - 1, FIRST_STAGE);
  return p === INSTALL_STAGE && !showsInstallStage(equipmentKind)
    ? Math.max(p - 1, FIRST_STAGE)
    : p;
}

export const STAGE_BANDS = {
  dev: [1, 2],
  approval: [3, 4, 5],
  production: [6],
  logistics: [7, 8, 9, 10],
} as const;

export type BandKey = keyof typeof STAGE_BANDS;

export function bandOf(stage: number): BandKey {
  for (const key of Object.keys(STAGE_BANDS) as BandKey[]) {
    if ((STAGE_BANDS[key] as readonly number[]).includes(stage)) return key;
  }
  return "logistics";
}

// 5-bucket color grouping (cycle every 2 stages) for StageBadge — was a
// 6-bucket scheme hardcoded to the old 12-stage total.
export function colorBucket(stage: number): 1 | 2 | 3 | 4 | 5 {
  return Math.min(5, Math.ceil(stage / 2)) as 1 | 2 | 3 | 4 | 5;
}
