import { StageBadge } from "../../components/StageBadge/StageBadge";
import { groupColor } from "../../lib/colors";
import type { components } from "../../api/schema";
import styles from "./TaskCard.module.css";

type TaskOut = components["schemas"]["TaskOut"];

/** Compact card used in the Kanban board columns. */
export function TaskCard({ task }: { task: TaskOut }) {
  const dlClass = task.days_left <= 7 ? styles.urgent : task.days_left <= 14 ? styles.warn : "";
  return (
    <div className={styles.card}>
      <div className={styles.top}>
        <div className={styles.dot} style={{ background: groupColor(task.group) }} />
        <span className={styles.code}>{task.code}</span>
        <span className={[styles.deadline, dlClass].join(" ")}>{task.days_left}д</span>
      </div>
      <div className={styles.name}>{task.name}</div>
      <div className={styles.meta}>
        {task.brand} · Гр.{task.group}
      </div>
      <div className={styles.stageRow}>
        <StageBadge stage={task.stage} label={task.stage_name} />
      </div>
    </div>
  );
}
