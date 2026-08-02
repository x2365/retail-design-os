import { ProgressBar } from "../../components/ProgressBar/ProgressBar";
import { useGroups } from "../../api/queries/groups";
import { formatMoneyShort, kopToRub } from "../../lib/money";
import styles from "./BudgetMini.module.css";

export function BudgetMini() {
  const { data, isLoading } = useGroups();

  if (isLoading) return <p style={{ color: "var(--text3)", fontSize: 12 }}>Загрузка…</p>;

  return (
    <div>
      {(data ?? []).map((g) => {
        const planned = kopToRub(g.budget_planned);
        const spent = kopToRub(g.budget_spent);
        const pct = planned > 0 ? Math.round((spent / planned) * 100) : 0;
        return (
          <div className={styles.group} key={g.code}>
            <div className={styles.header}>
              <div className={styles.dot} style={{ background: g.color }} />
              <div className={styles.name}>{g.name}</div>
              <div className={styles.total}>
                {formatMoneyShort(spent)} / {formatMoneyShort(planned)} ₽
              </div>
            </div>
            <div className={styles.barWrap}>
              <ProgressBar pct={pct} color={pct >= 100 ? "red" : pct >= 80 ? "amber" : "blue"} />
            </div>
            <div className={styles.foot}>
              <span>{pct}% освоено</span>
              <span>остаток {formatMoneyShort(Math.max(0, planned - spent))} ₽</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
