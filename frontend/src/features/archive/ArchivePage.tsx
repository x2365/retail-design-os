import { useMemo, useState } from "react";

import { Badge } from "../../components/Badge/Badge";
import { Panel } from "../../components/Panel/Panel";
import { useAuth } from "../../auth/AuthContext";
import { apiErrorMessage } from "../../api/client";
import { useTasks } from "../../api/queries/tasks";
import { useDeleteTask } from "../../api/queries/taskDetail";
import type { components } from "../../api/schema";
import { formatMoney, kopToRub } from "../../lib/money";
import forms from "../../styles/forms.module.css";
import { TaskDetailModal } from "../tasks/detail/TaskDetailModal";

type Task = components["schemas"]["TaskOut"];

const cellStyle: React.CSSProperties = {
  padding: "9px 10px",
  fontSize: 12,
  borderBottom: "1px solid var(--border)",
};

export default function ArchivePage() {
  const { data, isLoading } = useTasks({ page_size: 200 });
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<string | null>(null);

  const closed = useMemo(() => {
    let rows = (data?.items ?? []).filter((t) => t.stage >= 12);
    const q = search.trim().toLowerCase();
    if (q) {
      rows = rows.filter((t) =>
        `${t.code} ${t.name} ${t.brand} ${t.group}`.toLowerCase().includes(q),
      );
    }
    return rows;
  }, [data, search]);

  return (
    <Panel title="АРХИВ ЗАДАЧ" count={isLoading ? undefined : closed.length}>
      {selected && <TaskDetailModal code={selected} onClose={() => setSelected(null)} />}
      <input
        className={forms.input}
        placeholder="Поиск по коду, названию, бренду…"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />
      {isLoading ? (
        <p style={{ color: "var(--text3)", fontSize: 12 }}>Загрузка…</p>
      ) : closed.length === 0 ? (
        <p style={{ color: "var(--text3)", fontSize: 12 }}>
          {search ? "Ничего не найдено" : "Закрытых задач пока нет"}
        </p>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              {["Код", "Название", "Бренд", "Группа", "Дедлайн", "Бюджет", ""].map((h) => (
                <th
                  key={h}
                  style={{
                    textAlign: "left",
                    fontSize: 9,
                    color: "var(--text3)",
                    padding: "8px 10px",
                    borderBottom: "1px solid var(--border)",
                  }}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {closed.map((t) => (
              <ArchiveRow
                key={t.code}
                task={t}
                isAdmin={isAdmin}
                onOpen={() => setSelected(t.code)}
              />
            ))}
          </tbody>
        </table>
      )}
    </Panel>
  );
}

function ArchiveRow({
  task,
  isAdmin,
  onOpen,
}: {
  task: Task;
  isAdmin: boolean;
  onOpen: () => void;
}) {
  const deleteTask = useDeleteTask(task.code);
  const [error, setError] = useState("");

  async function handleDelete(e: React.MouseEvent) {
    e.stopPropagation();
    if (!confirm(`Удалить задачу ${task.code} безвозвратно?`)) return;
    setError("");
    try {
      await deleteTask.mutateAsync();
    } catch (err) {
      setError(apiErrorMessage(err, "Не удалось удалить задачу"));
    }
  }

  return (
    <tr style={{ cursor: "pointer" }} onClick={onOpen}>
      <td style={cellStyle}>
        <Badge color="gray">{task.code}</Badge>
      </td>
      <td style={cellStyle}>{task.name}</td>
      <td style={cellStyle}>{task.brand}</td>
      <td style={cellStyle}>Гр.{task.group}</td>
      <td style={cellStyle}>{task.deadline ?? "—"}</td>
      <td style={cellStyle}>{formatMoney(kopToRub(task.budget))}</td>
      <td style={cellStyle}>
        {isAdmin && (
          <button
            onClick={handleDelete}
            disabled={deleteTask.isPending}
            title={error || "Удалить задачу"}
            style={{
              background: "none",
              border: "none",
              color: error ? "var(--danger)" : "var(--text3)",
              cursor: "pointer",
            }}
          >
            🗑
          </button>
        )}
      </td>
    </tr>
  );
}
