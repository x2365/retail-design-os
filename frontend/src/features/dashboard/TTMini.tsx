import { Badge } from "../../components/Badge/Badge";
import { ProgressBar } from "../../components/ProgressBar/ProgressBar";
import { useTT } from "../../api/queries/tt";
import styles from "./TTMini.module.css";

export function TTMini() {
  const { data, isLoading } = useTT();

  if (isLoading) return <p style={{ color: "var(--text3)", fontSize: 12 }}>Загрузка…</p>;
  const rows = data ?? [];

  if (rows.length === 0) {
    return (
      <div style={{ color: "var(--text3)", fontSize: 12 }}>
        Нет активных лончей с доставками в ТТ
      </div>
    );
  }

  return (
    <table className={styles.table}>
      <thead>
        <tr>
          <th>Задача</th>
          <th>Бренд</th>
          <th>Всего ТТ</th>
          <th>Получили</th>
          <th>Неполный объём</th>
          <th>Не получили</th>
          <th>Прогресс</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((t) => {
          const pct = Math.round((t.tt_ok / Math.max(t.tt_total, 1)) * 100);
          return (
            <tr key={t.task}>
              <td>
                <Badge color="gray">{t.task}</Badge>
              </td>
              <td>{t.brand}</td>
              <td>{t.tt_total}</td>
              <td>
                <span className={[styles.status, styles.ok].join(" ")}>✓ {t.tt_ok}</span>
              </td>
              <td>
                <span className={[styles.status, styles.partial].join(" ")}>~ {t.tt_partial}</span>
              </td>
              <td>
                <span
                  className={[styles.status, t.tt_miss > 0 ? styles.missing : styles.waiting].join(
                    " ",
                  )}
                >
                  ✗ {t.tt_miss}
                </span>
              </td>
              <td className={styles.progressCell}>
                <ProgressBar
                  pct={pct}
                  color={pct === 100 ? "green" : pct > 50 ? "blue" : "amber"}
                />
                <div className={styles.progressLabel}>{pct}%</div>
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
