import { useState } from "react";

import { Button } from "../../components/Button/Button";
import { Panel } from "../../components/Panel/Panel";
import { KpiCard, KpiRow } from "../../components/KpiCard/KpiCard";
import { useAuth } from "../../auth/AuthContext";
import { useDashboardKpis } from "../../api/queries/dashboard";
import { useApprovals } from "../../api/queries/approvals";
import { formatMoney, kopToRub } from "../../lib/money";
import { ActiveTasksPanel } from "../tasks/ActiveTasksPanel";
import { TaskCreateModal } from "../tasks/TaskCreateModal";
import { TaskDetailModal } from "../tasks/detail/TaskDetailModal";
import { ApprovalsMini } from "./ApprovalsMini";
import { BudgetMini } from "./BudgetMini";
import { TTMini } from "./TTMini";
import styles from "./DashboardPage.module.css";

export default function DashboardPage() {
  const { data: k, isLoading } = useDashboardKpis();
  const { data: pendingApprovals } = useApprovals("pending");
  const pendingCount = pendingApprovals?.length ?? 0;
  const { isEditor } = useAuth();
  const [creating, setCreating] = useState(false);
  // "Открыть →" on Ожидают решения opens the task right here instead of
  // navigating to Pipeline — no page change means no "where do I go back
  // to" problem, and the row it came from can be highlighted once closed.
  const [openedCode, setOpenedCode] = useState<string | null>(null);
  const [highlightCode, setHighlightCode] = useState<string | null>(null);
  function openTask(code: string) {
    setOpenedCode(code);
    setHighlightCode(code);
  }

  if (isLoading || !k) return <p style={{ color: "var(--text2)" }}>Загрузка…</p>;

  const budgetSpent = kopToRub(k.budget_spent);
  const budgetTotal = kopToRub(k.budget_total);
  const budgetPct = budgetTotal > 0 ? Math.round((budgetSpent / budgetTotal) * 100) : 0;

  return (
    <div>
      {openedCode && (
        <TaskDetailModal code={openedCode} onClose={() => setOpenedCode(null)} />
      )}
      {isEditor && (
        <div className={styles.topActions}>
          <Button variant="primary" onClick={() => setCreating(true)}>
            + Создать задачу
          </Button>
        </div>
      )}
      {creating && <TaskCreateModal onClose={() => setCreating(false)} />}

      <KpiRow>
        <KpiCard
          accent="blue"
          label="Активных задач"
          value={k.active_tasks}
          sub={`из ${k.brands_count} брендов`}
        />
        <KpiCard
          accent="amber"
          label="Срок < 14 дней"
          value={k.due_soon}
          valueColor="var(--warn)"
          sub="требуют внимания"
        />
        <KpiCard
          accent="green"
          label="Завершено"
          value={k.completed}
          valueColor="var(--accent3)"
          sub="лончей"
          delta={(k.on_time_rate == null ? "—" : `${k.on_time_rate}%`) + " on-time"}
          deltaDirection="up"
        />
        <KpiCard
          accent="purple"
          label="Бюджет"
          value={formatMoney(budgetSpent)}
          valueFontSize={16}
          sub={`из ${formatMoney(budgetTotal)} плана`}
          delta={`${budgetPct}% освоено`}
          deltaDirection="up"
        />
        <KpiCard
          accent="red"
          label="ТТ без подтв."
          value={k.tt_unconfirmed}
          valueColor="var(--danger)"
          sub={`из ${k.points_total} точек`}
          delta="нужна проверка"
          deltaDirection="down"
        />
      </KpiRow>

      <div className={styles.gridMain}>
        <ActiveTasksPanel highlightCode={highlightCode} />

        <div className={styles.sideStack}>
          <Panel title="ОЖИДАЮТ РЕШЕНИЯ" count={pendingCount} countAlert>
            <ApprovalsMini onOpenTask={openTask} />
          </Panel>
          <Panel title="БЮДЖЕТ ПО ГРУППАМ">
            <BudgetMini />
          </Panel>
        </div>
      </div>

      <Panel title="СТАТУС ТОРГОВЫХ ТОЧЕК — АКТИВНЫЕ ЛОНЧИ">
        <TTMini />
      </Panel>
    </div>
  );
}
