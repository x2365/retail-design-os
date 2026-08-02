import { useMemo, useState } from "react";

import { Badge } from "../../components/Badge/Badge";
import { Panel } from "../../components/Panel/Panel";
import { useTasks } from "../../api/queries/tasks";
import { formatMoney, kopToRub } from "../../lib/money";
import forms from "../../styles/forms.module.css";
import { TaskDetailModal } from "../tasks/detail/TaskDetailModal";

export default function ArchivePage() {
  const { data, isLoading } = useTasks({ page_size: 200 });
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
              {["Код", "Название", "Бренд", "Группа", "Дедлайн", "Бюджет"].map((h) => (
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
              <tr key={t.code} style={{ cursor: "pointer" }} onClick={() => setSelected(t.code)}>
                <td
                  style={{
                    padding: "9px 10px",
                    fontSize: 12,
                    borderBottom: "1px solid var(--border)",
                  }}
                >
                  <Badge color="gray">{t.code}</Badge>
                </td>
                <td
                  style={{
                    padding: "9px 10px",
                    fontSize: 12,
                    borderBottom: "1px solid var(--border)",
                  }}
                >
                  {t.name}
                </td>
                <td
                  style={{
                    padding: "9px 10px",
                    fontSize: 12,
                    borderBottom: "1px solid var(--border)",
                  }}
                >
                  {t.brand}
                </td>
                <td
                  style={{
                    padding: "9px 10px",
                    fontSize: 12,
                    borderBottom: "1px solid var(--border)",
                  }}
                >
                  Гр.{t.group}
                </td>
                <td
                  style={{
                    padding: "9px 10px",
                    fontSize: 12,
                    borderBottom: "1px solid var(--border)",
                  }}
                >
                  {t.deadline ?? "—"}
                </td>
                <td
                  style={{
                    padding: "9px 10px",
                    fontSize: 12,
                    borderBottom: "1px solid var(--border)",
                  }}
                >
                  {formatMoney(kopToRub(t.production_cost))}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Panel>
  );
}
