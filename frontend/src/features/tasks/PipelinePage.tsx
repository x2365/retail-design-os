import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { Panel } from "../../components/Panel/Panel";
import { useTasks } from "../../api/queries/tasks";
import { LAST_STAGE } from "../../lib/stages";
import { TaskDetailModal } from "./detail/TaskDetailModal";
import { KANBAN_COLUMNS } from "./stageBands";
import { TaskCard } from "./TaskCard";
import styles from "./PipelinePage.module.css";

export default function PipelinePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [selected, setSelected] = useState<string | null>(null);

  // Deep link from Approvals ("Перейти к задаче →" for gate-based approvals
  // that must be resolved inside the task card, not via approve/reject).
  useEffect(() => {
    const open = searchParams.get("open");
    if (open) {
      setSelected(open);
      searchParams.delete("open");
      setSearchParams(searchParams, { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // One real server-side filtered request per band (?band=dev|approval|...),
  // replacing the old app's approach of loading everything and bucketing by
  // a second, hand-maintained copy of the stage ranges.
  const dev = useTasks({ band: "dev", page_size: 200 });
  const approval = useTasks({ band: "approval", page_size: 200 });
  const production = useTasks({ band: "production", page_size: 200 });
  const logistics = useTasks({ band: "logistics", page_size: 200 });

  const byBand = { dev, approval, production, logistics };

  return (
    <div className={styles.board}>
      {selected && <TaskDetailModal code={selected} onClose={() => setSelected(null)} />}
      {KANBAN_COLUMNS.map((col) => {
        const query = byBand[col.key];
        // The Kanban board is "work in flight" — closed tasks (stage 12,
        // included in the backend's "logistics" band) belong in Archive.
        const tasks = (query.data?.items ?? []).filter((t) => t.stage < LAST_STAGE);
        return (
          <Panel
            key={col.key}
            title={col.title}
            leading={<div className={styles.colDot} style={{ background: col.color }} />}
            count={query.isLoading ? undefined : tasks.length}
          >
            <div className={styles.colBody}>
              {query.isLoading ? (
                <p className={styles.empty}>Загрузка…</p>
              ) : tasks.length === 0 ? (
                <p className={styles.empty}>Нет задач</p>
              ) : (
                tasks.map((t) => (
                  <TaskCard key={t.code} task={t} onClick={() => setSelected(t.code)} />
                ))
              )}
            </div>
          </Panel>
        );
      })}
    </div>
  );
}
