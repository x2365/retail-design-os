import { useState } from "react";

import { Badge } from "../../components/Badge/Badge";
import { Button } from "../../components/Button/Button";
import { KpiCard } from "../../components/KpiCard/KpiCard";
import { Panel } from "../../components/Panel/Panel";
import { useAuth } from "../../auth/AuthContext";
import { useGroups } from "../../api/queries/groups";
import { useBudgetLog, useSaveGroupPlan } from "../../api/queries/budget";
import { formatMoney, kopToRub } from "../../lib/money";
import styles from "./BudgetPage.module.css";

const ACCENTS = ["blue", "green", "amber"] as const;

export default function BudgetPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const { data: groups, isLoading } = useGroups();
  const savePlan = useSaveGroupPlan();
  const [drafts, setDrafts] = useState<Record<string, number>>({});

  return (
    <div>
      <div className={styles.cards}>
        {isLoading
          ? null
          : (groups ?? []).map((g, i) => {
              const planned = kopToRub(g.budget_planned);
              const spent = kopToRub(g.budget_spent);
              const pct = planned ? Math.round((spent / planned) * 100) : 0;
              const draft = drafts[g.code] ?? planned;
              return (
                <KpiCard
                  key={g.code}
                  accent={ACCENTS[i % 3]}
                  label={`${g.name} — план`}
                  value={formatMoney(planned)}
                  sub={`Освоено ${formatMoney(spent)} · ${pct}%`}
                  delta={
                    isAdmin ? (
                      <div className={styles.editRow}>
                        <input
                          type="number"
                          className={styles.planInput}
                          value={draft}
                          onFocus={(e) => e.target.select()}
                          onChange={(e) =>
                            setDrafts((d) => ({ ...d, [g.code]: Number(e.target.value) }))
                          }
                        />
                        <Button
                          variant="primary"
                          disabled={savePlan.isPending}
                          onClick={() =>
                            savePlan.mutate({
                              code: g.code,
                              budgetPlannedKop: Math.round(draft * 100),
                            })
                          }
                        >
                          Сохранить план
                        </Button>
                      </div>
                    ) : undefined
                  }
                />
              );
            })}
      </div>

      {isAdmin ? (
        <BudgetLog />
      ) : (
        <p style={{ color: "var(--text3)", fontSize: 11 }}>
          Редактировать бюджет может только администратор.
        </p>
      )}
    </div>
  );
}

const ENTITY_TYPE_LABELS: Record<string, string> = {
  task: "Задача",
  group: "Группа",
  brand: "Бренд",
  equipment: "Изделие",
  retail_point: "Точка",
  document: "Документ",
};

function BudgetLog() {
  const { data, isLoading } = useBudgetLog();
  const [open, setOpen] = useState(false);
  const rows = data ?? [];

  return (
    <Panel
      title={`ЖУРНАЛ ИЗМЕНЕНИЙ (${rows.length})`}
      actions={
        <button
          onClick={() => setOpen((o) => !o)}
          style={{ background: "none", border: "none", color: "var(--text2)", cursor: "pointer" }}
        >
          {open ? "▾" : "▸"}
        </button>
      }
    >
      {open &&
        (isLoading ? (
          <p style={{ color: "var(--text3)", fontSize: 11 }}>Загрузка…</p>
        ) : rows.length === 0 ? (
          <p style={{ color: "var(--text3)", fontSize: 11 }}>Изменений пока нет</p>
        ) : (
          <table className={styles.logTable}>
            <thead>
              <tr>
                <th>Когда</th>
                <th>Кто</th>
                <th>Объект</th>
                <th>Код</th>
                <th>Поле</th>
                <th>Было</th>
                <th>Стало</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id}>
                  <td style={{ color: "var(--text3)" }}>{r.at}</td>
                  <td>{r.who}</td>
                  <td style={{ color: "var(--text3)", fontSize: 11 }}>
                    {ENTITY_TYPE_LABELS[r.entity_type] ?? r.entity_type}
                  </td>
                  <td>
                    <Badge color="gray">{r.task}</Badge>
                  </td>
                  <td>{r.field}</td>
                  <td style={{ color: r.field === "Удаление" ? "var(--danger)" : "var(--text3)" }}>
                    {r.old}
                  </td>
                  <td>
                    <b>{r.new}</b>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ))}
    </Panel>
  );
}
