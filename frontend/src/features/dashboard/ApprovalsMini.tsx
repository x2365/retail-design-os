import { Link, useNavigate } from "react-router-dom";

import { useApprovals, useApproveApproval } from "../../api/queries/approvals";
import styles from "./ApprovalsMini.module.css";

export function ApprovalsMini({ onOpenTask }: { onOpenTask: (code: string) => void }) {
  const { data, isLoading } = useApprovals("pending");
  const approve = useApproveApproval();
  const navigate = useNavigate();

  if (isLoading) return <p style={{ color: "var(--text3)", fontSize: 12 }}>Загрузка…</p>;
  const pending = data ?? [];

  if (pending.length === 0) {
    return (
      <div style={{ color: "var(--text3)", fontSize: 12, padding: 8 }}>
        Нет ожидающих согласований
      </div>
    );
  }

  return (
    <div>
      {pending.map((a) => {
        // Narrowed to a local const: TS can't carry a truthy-check on
        // a.task (nullable in the schema) through into the onClick closure
        // below, since it can't prove the property won't change by the time
        // the closure runs — a local const it can.
        const taskCode = a.task;
        return (
          <div
            key={a.id}
            className={styles.item}
            style={{ cursor: "pointer" }}
            onClick={() => navigate("/approvals")}
            title="Открыть согласования"
          >
            <div className={styles.avatar} style={{ background: `${a.color}22`, color: a.color }}>
              {a.avatar}
            </div>
            <div className={styles.info}>
              <div className={styles.name}>{a.from_name}</div>
              <div className={styles.task}>{a.task}</div>
            </div>
            <div className={styles.actions} onClick={(e) => e.stopPropagation()}>
              {a.id < 0 && taskCode ? (
                <button className={styles.reject} onClick={() => onOpenTask(taskCode)}>
                  Открыть →
                </button>
              ) : (
                <>
                  <button className={styles.approve} onClick={() => approve.mutate(a.id)}>
                    ✓
                  </button>
                  <Link
                    to="/approvals"
                    className={styles.reject}
                    style={{ textDecoration: "none" }}
                  >
                    ✗
                  </Link>
                </>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
