import { KpiCard, KpiRow } from "../../components/KpiCard/KpiCard";
import { Panel } from "../../components/Panel/Panel";
import { ProgressBar } from "../../components/ProgressBar/ProgressBar";
import { useMetrics } from "../../api/queries/metrics";
import { STAGE_LABELS } from "../../lib/stages";
import styles from "./MetricsPage.module.css";

export default function MetricsPage() {
  const { data, isLoading } = useMetrics();

  if (isLoading || !data) return <p style={{ color: "var(--text2)" }}>Загрузка…</p>;

  const wipEntries = Object.entries(data.wip_by_stage)
    .map(([stage, count]) => [Number(stage), count] as const)
    .sort((a, b) => a[0] - b[0]);
  const wipTotal = wipEntries.reduce((sum, [, count]) => sum + count, 0);
  const wipMax = Math.max(1, ...wipEntries.map(([, count]) => count));

  const throughputThisWeek = data.throughput_by_week.at(-1)?.count ?? 0;
  const throughputMax = Math.max(1, ...data.throughput_by_week.map((w) => w.count));

  return (
    <div>
      <p className={styles.intro}>
        Flow-метрики процесса, посчитанные из истории переходов между этапами (
        <code>TaskStageHistory</code>) — WIP, Lead Time, Throughput и Rework Rate уже полностью
        вычислимы из существующих данных. Conversion Rate, Cost per Outcome и Customer Outcome сюда
        не входят — для них не хватает конкретных полей в модели данных.
      </p>

      <KpiRow>
        <KpiCard
          accent="blue"
          label="Lead Time"
          value={data.lead_time_avg_days != null ? `${data.lead_time_avg_days} дн.` : "—"}
          sub="в среднем от создания до закрытия"
        />
        <KpiCard
          accent="green"
          label="Throughput"
          value={throughputThisWeek}
          sub="задач закрыто за эту неделю"
        />
        <KpiCard accent="purple" label="WIP" value={wipTotal} sub="задач сейчас в работе" />
        <KpiCard
          accent="amber"
          label="Rework Rate"
          value={`${data.rework_rate}%`}
          sub={`из ${data.total_transitions} переходов между этапами`}
        />
      </KpiRow>

      <div className={styles.grid}>
        <Panel title="WIP ПО ЭТАПАМ">
          <div className={styles.barList}>
            {wipEntries.map(([stage, count]) => (
              <div className={styles.barRow} key={stage}>
                <span className={styles.barLabel}>{STAGE_LABELS[stage] ?? stage}</span>
                <div className={styles.barTrack}>
                  <ProgressBar pct={(count / wipMax) * 100} color="blue" />
                </div>
                <span className={styles.barValue}>{count}</span>
              </div>
            ))}
          </div>
        </Panel>

        <Panel title="THROUGHPUT ПО НЕДЕЛЯМ">
          <div className={styles.barList}>
            {data.throughput_by_week.map((w) => (
              <div className={styles.barRow} key={w.week}>
                <span className={styles.barLabel}>{w.week}</span>
                <div className={styles.barTrack}>
                  <ProgressBar pct={(w.count / throughputMax) * 100} color="green" />
                </div>
                <span className={styles.barValue}>{w.count}</span>
              </div>
            ))}
          </div>
        </Panel>
      </div>
    </div>
  );
}
