import { useState } from "react";

import { Panel } from "../../components/Panel/Panel";
import { useTasks } from "../../api/queries/tasks";
import { LAST_STAGE } from "../../lib/stages";
import type { components } from "../../api/schema";
import { TaskDetailModal } from "./detail/TaskDetailModal";
import { TaskRow } from "./TaskRow";
import forms from "../../styles/forms.module.css";
import styles from "./PipelineTabs.module.css";

type TaskOut = components["schemas"]["TaskOut"];
type Filter = "all" | "urgent";
type SortKey = "deadline" | "group" | "created";

const TABS: { key: Filter; label: string }[] = [
  { key: "all", label: "Все" },
  { key: "urgent", label: "Срочные" },
];

const PANEL_TITLES: Record<Filter, string> = {
  all: "АКТИВНЫЕ ЗАДАЧИ",
  urgent: "СРОЧНЫЕ ЗАДАЧИ",
};

const SORT_OPTIONS: { key: SortKey; label: string }[] = [
  { key: "deadline", label: "По дедлайну" },
  { key: "group", label: "По группе" },
  { key: "created", label: "По дате создания" },
];

// task.deadline is "DD.MM.YY" (backend serializers._fmt_date), not ISO —
// must parse before comparing, plain string compare would sort by day first.
function parseDeadline(s: string): number {
  const [d, m, y] = s.split(".").map(Number);
  return Date.UTC(2000 + y, m - 1, d);
}

function compareTasks(a: TaskOut, b: TaskOut, sort: SortKey): number {
  switch (sort) {
    case "group":
      return a.group.localeCompare(b.group); // stable sort keeps deadline order as tie-break
    case "created":
      // created_at is a full ISO datetime string — newest first
      if (!a.created_at && !b.created_at) return 0;
      if (!a.created_at) return 1;
      if (!b.created_at) return -1;
      return b.created_at.localeCompare(a.created_at);
    case "deadline":
    default:
      // mirrors backend's .order_by(Task.deadline_tt.asc().nullslast())
      if (!a.deadline && !b.deadline) return 0;
      if (!a.deadline) return 1;
      if (!b.deadline) return -1;
      return parseDeadline(a.deadline) - parseDeadline(b.deadline);
  }
}

/** Preview of active tasks embedded in the Dashboard — same underlying
 * TaskRow the full pipeline board (PipelinePage) reuses. Filtering happens
 * client-side over one already-small fetched page, matching the old app
 * (a single TASKS array filtered in memory), not three separate endpoints. */
export function ActiveTasksPanel() {
  const [filter, setFilter] = useState<Filter>("all");
  const [sort, setSort] = useState<SortKey>("deadline");
  const [selected, setSelected] = useState<string | null>(null);
  const { data, isLoading } = useTasks({ page_size: 50 });

  if (isLoading)
    return (
      <Panel title={PANEL_TITLES[filter]}>
        <p style={{ color: "var(--text3)", fontSize: 12 }}>Загрузка…</p>
      </Panel>
    );

  let tasks = (data?.items ?? []).filter((t) => t.stage < LAST_STAGE); // closed -> Archive
  // "Срочные" = дедлайн ≤ 7 дней — тот же порог, что уже красит TaskRow
  // красным (TaskRow.tsx). task.urgent — отдельный ручной флаг, который
  // никак не выставляется через UI (ни при создании, ни в карточке), так
  // что фильтровать по нему было по факту невозможно.
  if (filter === "urgent") tasks = tasks.filter((t) => t.days_left <= 7);
  tasks = [...tasks].sort((a, b) => compareTasks(a, b, sort));

  return (
    <Panel title={PANEL_TITLES[filter]} count={tasks.length}>
      {selected && <TaskDetailModal code={selected} onClose={() => setSelected(null)} />}
      <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 16 }}>
        <div className={styles.tabs} style={{ flex: 1, marginBottom: 0 }}>
          {TABS.map((t) => (
            <button
              key={t.key}
              className={[styles.tab, filter === t.key ? styles.tabActive : ""].join(" ")}
              onClick={() => setFilter(t.key)}
            >
              {t.label}
            </button>
          ))}
        </div>
        <select
          className={forms.select}
          style={{ width: "auto", flexShrink: 0 }}
          value={sort}
          onChange={(e) => setSort(e.target.value as SortKey)}
        >
          {SORT_OPTIONS.map((o) => (
            <option key={o.key} value={o.key}>
              {o.label}
            </option>
          ))}
        </select>
      </div>

      {tasks.length === 0 ? (
        <p style={{ color: "var(--text3)", fontSize: 12 }}>Нет задач</p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {tasks.map((t) => (
            <TaskRow key={t.code} task={t} onClick={() => setSelected(t.code)} />
          ))}
        </div>
      )}
    </Panel>
  );
}
