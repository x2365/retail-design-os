import { useState } from "react";

import { useTasks } from "../../api/queries/tasks";
import { TaskRow } from "./TaskRow";
import styles from "./PipelineTabs.module.css";

type Filter = "all" | "urgent" | "approval";

const TABS: { key: Filter; label: string }[] = [
  { key: "all", label: "Все" },
  { key: "urgent", label: "Срочные" },
  { key: "approval", label: "На утверждении" },
];

/** Preview of active tasks embedded in the Dashboard — same underlying
 * TaskRow the full pipeline board (PipelinePage) reuses. Filtering happens
 * client-side over one already-small fetched page, matching the old app
 * (a single TASKS array filtered in memory), not three separate endpoints. */
export function ActiveTasksPanel() {
  const [filter, setFilter] = useState<Filter>("all");
  const { data, isLoading } = useTasks({ page_size: 50 });

  if (isLoading) return <p style={{ color: "var(--text3)", fontSize: 12 }}>Загрузка…</p>;

  let tasks = (data?.items ?? []).filter((t) => t.stage < 12); // closed -> Archive
  if (filter === "urgent") tasks = tasks.filter((t) => t.urgent);
  if (filter === "approval") tasks = tasks.filter((t) => t.stage >= 3 && t.stage <= 6);

  return (
    <div>
      <div className={styles.tabs}>
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

      {tasks.length === 0 ? (
        <p style={{ color: "var(--text3)", fontSize: 12 }}>Нет задач</p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {tasks.map((t) => (
            <TaskRow key={t.code} task={t} />
          ))}
        </div>
      )}
    </div>
  );
}
