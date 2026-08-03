import { Link } from "react-router-dom";

import { Badge } from "../../components/Badge/Badge";
import { Panel } from "../../components/Panel/Panel";
import { useApprovals, useApproveApproval, useRejectApproval } from "../../api/queries/approvals";
import styles from "./ApprovalsPage.module.css";

const STATUS_LABEL: Record<string, string> = {
  approved: "Согласовано",
  rejected: "Отклонено",
  pending: "Ожидает",
};
const STATUS_COLOR: Record<string, "green" | "red" | "amber"> = {
  approved: "green",
  rejected: "red",
  pending: "amber",
};

export default function ApprovalsPage() {
  const { data, isLoading } = useApprovals("all");
  const approve = useApproveApproval();
  const reject = useRejectApproval();

  return (
    <Panel title="СОГЛАСОВАНИЯ" count={isLoading ? undefined : data?.length}>
      {isLoading ? (
        <p className={styles.empty}>Загрузка…</p>
      ) : !data || data.length === 0 ? (
        <p className={styles.empty}>
          Нет согласований, ожидающих решения. Задача появляется здесь, когда доходит до этапа
          «Согласования», «Бюджет и КП» или «Образец».
        </p>
      ) : (
        <>
          <p className={styles.hint}>
            Часть строк — это задачи, зависшие на внутреннем гейте этапа: решение принимается в
            карточке задачи, здесь только ссылка на неё. Остальные можно утвердить/отклонить прямо
            тут.
          </p>
          {data.map((a) => {
            const isGate = a.id < 0;
            const color = STATUS_COLOR[a.status] ?? "amber";
            const label = STATUS_LABEL[a.status] ?? a.status;
            return (
              <div className={styles.item} key={a.id}>
                <div
                  className={styles.avatar}
                  style={{ background: `${a.color}22`, color: a.color }}
                >
                  {a.avatar}
                </div>
                <div className={styles.info}>
                  <div className={styles.topRow}>
                    <span className={styles.name}>{a.from_name}</span>
                    <Badge color="blue">{a.type}</Badge>
                    {isGate ? (
                      <Badge color="gray">гейт в карточке</Badge>
                    ) : (
                      <Badge color={color}>{label}</Badge>
                    )}
                  </div>
                  <div className={styles.taskLine}>{a.summary}</div>
                  {a.comment && <div className={styles.taskLine}>💬 {a.comment}</div>}
                </div>
                <div className={styles.actions}>
                  {isGate ? (
                    <Link
                      to={`/pipeline?open=${a.task}`}
                      className={styles.approve}
                      style={{ textDecoration: "none" }}
                    >
                      Перейти к задаче →
                    </Link>
                  ) : a.status === "pending" ? (
                    <>
                      <button className={styles.approve} onClick={() => approve.mutate(a.id)}>
                        ✓ Утвердить
                      </button>
                      <button className={styles.reject} onClick={() => reject.mutate(a.id)}>
                        ✗ Отклонить
                      </button>
                    </>
                  ) : null}
                </div>
              </div>
            );
          })}
        </>
      )}
    </Panel>
  );
}
