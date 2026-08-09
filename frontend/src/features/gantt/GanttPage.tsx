import { useMemo, useState } from "react";

import { Panel } from "../../components/Panel/Panel";
import { useTasks } from "../../api/queries/tasks";
import type { components } from "../../api/schema";
import { parseRuDate } from "../../lib/dates";
import { LAST_STAGE, bandOf } from "../../lib/stages";
import { TaskDetailModal } from "../tasks/detail/TaskDetailModal";
import styles from "./GanttPage.module.css";

type TaskOut = components["schemas"]["TaskOut"];

const DAY_MS = 86_400_000;

function barColor(stage: number): string {
  const band = bandOf(stage);
  if (band === "logistics") return "var(--accent3)";
  if (band === "dev") return "var(--accent2)";
  return "var(--accent)"; // approval/production
}

/** Timeline built from each task's real created_at -> deadline range —
 * replaces the old app's renderGantt(), which faked bar position with
 * Math.random() instead of using any actual date field. `deadline` is a
 * pre-formatted "дд.мм.гг" display string (see serializers.py), not ISO,
 * so it needs parseRuDate rather than `new Date(...)`. */
export default function GanttPage() {
  const { data, isLoading } = useTasks({ page_size: 200 });
  const [selected, setSelected] = useState<string | null>(null);

  const rows = useMemo(() => {
    const withDates: { task: TaskOut; start: number; end: number }[] = [];
    for (const t of data?.items ?? []) {
      if (t.stage >= LAST_STAGE || !t.created_at) continue;
      const start = new Date(t.created_at).getTime();
      const end = parseRuDate(t.deadline);
      if (Number.isFinite(start) && end !== null && end > start) {
        withDates.push({ task: t, start, end });
      }
    }
    return withDates;
  }, [data]);

  const now = Date.now();
  const windowStart = Math.min(now - 30 * DAY_MS, ...rows.map((r) => r.start));
  const windowEnd = Math.max(now + 30 * DAY_MS, ...rows.map((r) => r.end));
  const span = windowEnd - windowStart || 1;
  const pct = (t: number) => ((t - windowStart) / span) * 100;
  const todayPos = pct(now);

  const fmt = (t: number) =>
    new Date(t).toLocaleDateString("ru-RU", { day: "2-digit", month: "short" });

  return (
    <Panel title="ТАЙМЛАЙН" count={isLoading ? undefined : rows.length}>
      {selected && <TaskDetailModal code={selected} onClose={() => setSelected(null)} />}
      {isLoading ? (
        <p style={{ color: "var(--text3)", fontSize: 12 }}>Загрузка…</p>
      ) : rows.length === 0 ? (
        <p style={{ color: "var(--text3)", fontSize: 12 }}>
          Нет задач с заданным дедлайном ТТ — таймлайну не из чего строить полосы.
        </p>
      ) : (
        <div className={styles.wrap}>
          <div className={styles.windowLabel}>
            {fmt(windowStart)} — {fmt(windowEnd)}
          </div>
          {rows.map(({ task, start, end }) => {
            const left = Math.max(0, pct(start));
            const width = Math.max(1.5, pct(end) - left);
            const progressPct = task.progress_pct;
            return (
              <div className={styles.row} key={task.code} onClick={() => setSelected(task.code)}>
                <div className={styles.label}>
                  {task.brand}
                  <br />
                  <span className={styles.code}>{task.code}</span>
                </div>
                <div className={styles.track}>
                  <div
                    className={styles.bar}
                    style={{
                      left: `${left}%`,
                      width: `${width}%`,
                      background: `color-mix(in srgb, ${barColor(task.stage)} 20%, transparent)`,
                      color: barColor(task.stage),
                    }}
                  >
                    {task.stage_name}
                  </div>
                  {todayPos >= 0 && todayPos <= 100 && (
                    <div className={styles.today} style={{ left: `${todayPos}%` }} />
                  )}
                </div>
                <div className={styles.pct}>{progressPct}%</div>
              </div>
            );
          })}

          <div className={styles.legend}>
            <div className={styles.legendItem}>
              <div className={styles.legendDot} style={{ background: "var(--accent2)" }} />
              Разработка
            </div>
            <div className={styles.legendItem}>
              <div className={styles.legendDot} style={{ background: "var(--accent)" }} />
              Согласование/Производство
            </div>
            <div className={styles.legendItem}>
              <div className={styles.legendDot} style={{ background: "var(--accent3)" }} />
              Логистика
            </div>
            <div className={styles.legendItem}>
              <div
                className={styles.legendDot}
                style={{ background: "var(--danger)", width: 2, height: 10, borderRadius: 0 }}
              />
              Сегодня
            </div>
          </div>
        </div>
      )}
    </Panel>
  );
}
