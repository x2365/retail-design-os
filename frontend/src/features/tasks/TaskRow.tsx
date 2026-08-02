import { Badge } from "../../components/Badge/Badge";
import { ProgressBar } from "../../components/ProgressBar/ProgressBar";
import { StageBadge } from "../../components/StageBadge/StageBadge";
import { groupColor } from "../../lib/colors";
import type { components } from "../../api/schema";
import styles from "./TaskRow.module.css";

type TaskOut = components["schemas"]["TaskOut"];

const TOTAL_STAGES = 12; // TaskStage enum length (backend/app/models/enums.py)

/** Full-detail row used in the Dashboard's "Активные задачи" panel — same
 * content as the old app's renderTasks() card (stage-pipeline dots +
 * progress bar), distinct from the compact Kanban TaskCard. */
export function TaskRow({ task, onClick }: { task: TaskOut; onClick?: () => void }) {
  const dlClass = task.days_left <= 7 ? styles.urgent : task.days_left <= 14 ? styles.warn : "";
  const dlIcon = task.days_left <= 7 ? "🔴" : task.days_left <= 14 ? "🟡" : "🟢";
  const pct = task.progress_pct;

  return (
    <div
      className={styles.card}
      onClick={onClick}
      style={onClick ? { cursor: "pointer" } : undefined}
    >
      <div className={styles.top}>
        <div className={styles.dot} style={{ background: groupColor(task.group) }} />
        <div style={{ flex: 1 }}>
          <div className={styles.name}>{task.name}</div>
          <div className={styles.metaRow}>
            <Badge color="gray">{task.code}</Badge>
            <span className={styles.metaText}>
              {task.brand} · Гр.{task.group}
            </span>
            <StageBadge stage={task.stage} label={task.stage_name} />
          </div>
        </div>
        <div className={[styles.deadline, dlClass].join(" ")}>
          {dlIcon} {task.days_left}д
        </div>
      </div>

      <div className={styles.stagePipeline}>
        {Array.from({ length: TOTAL_STAGES }, (_, i) => (
          <div
            key={i}
            className={[
              styles.stageDot,
              i < task.stage - 1
                ? styles.stageDotDone
                : i === task.stage - 1
                  ? styles.stageDotActive
                  : "",
            ].join(" ")}
          />
        ))}
      </div>

      <div className={styles.progressWrap}>
        <div className={styles.progressLabel}>
          <span>
            Этап {task.stage}/{TOTAL_STAGES}
          </span>
          <span>{pct}%</span>
        </div>
        <ProgressBar pct={pct} color={pct > 70 ? "green" : pct > 40 ? "blue" : "amber"} />
      </div>
    </div>
  );
}
