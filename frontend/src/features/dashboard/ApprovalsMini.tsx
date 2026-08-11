import { Link, useNavigate } from "react-router-dom";

import { useApprovals, useApproveApproval } from "../../api/queries/approvals";
import styles from "./ApprovalsMini.module.css";

export function ApprovalsMini() {
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
      {pending.map((a) => (
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
            {a.id < 0 ? (
              <Link
                to={`/pipeline?open=${a.task}`}
                className={styles.reject}
                style={{ textDecoration: "none" }}
              >
                Открыть →
              </Link>
            ) : (
              <>
                <button className={styles.approve} onClick={() => approve.mutate(a.id)}>
                  ✓
                </button>
                <Link to="/approvals" className={styles.reject} style={{ textDecoration: "none" }}>
                  ✗
                </Link>
              </>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
