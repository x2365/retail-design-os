import { Panel } from "../../components/Panel/Panel";
import { KpiCard, KpiRow } from "../../components/KpiCard/KpiCard";
import { useDashboardKpis } from "../../api/queries/dashboard";
import { useApprovals } from "../../api/queries/approvals";
import { formatMoney, kopToRub } from "../../lib/money";
import { ApprovalsMini } from "./ApprovalsMini";
import { BudgetMini } from "./BudgetMini";
import { TTMini } from "./TTMini";
import styles from "./DashboardPage.module.css";

export default function DashboardPage() {
  const { data: k, isLoading } = useDashboardKpis();
  const { data: pendingApprovals } = useApprovals("pending");
  const pendingCount = pendingApprovals?.length ?? 0;

  if (isLoading || !k) return <p style={{ color: "var(--text2)" }}>Загрузка…</p>;

  const budgetSpent = kopToRub(k.budget_spent);
  const budgetTotal = kopToRub(k.budget_total);
  const budgetPct = budgetTotal > 0 ? Math.round((budgetSpent / budgetTotal) * 100) : 0;

  return (
    <div>
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
        <Panel title="АКТИВНЫЕ ЗАДАЧИ" count={k.active_tasks}>
          <p className={styles.placeholder}>
            Список задач появится с экраном «Воронка задач» — следующий шаг рефакторинга.
          </p>
        </Panel>

        <div className={styles.sideStack}>
          <Panel title="ОЖИДАЮТ РЕШЕНИЯ" count={pendingCount} countAlert>
            <ApprovalsMini />
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
