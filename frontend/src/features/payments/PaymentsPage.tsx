import { useMemo, useState } from "react";

import { Badge } from "../../components/Badge/Badge";
import { Button } from "../../components/Button/Button";
import { Panel } from "../../components/Panel/Panel";
import { useAuth } from "../../auth/AuthContext";
import { apiErrorMessage, downloadFile } from "../../api/client";
import { usePayments, useUpdatePaymentStatus, useUpsertPayment } from "../../api/queries/payments";
import forms from "../../styles/forms.module.css";
import styles from "./PaymentsPage.module.css";

const PAYMENT_STATUS_OPTIONS: { value: string; label: string }[] = [
  { value: "unpaid", label: "Авто (по факту оплаты)" },
  { value: "registry", label: "Отправлен в реестр" },
  { value: "queued", label: "Заведён на оплату" },
  { value: "prepaid", label: "Предоплачен" },
  { value: "paid", label: "Оплачено" },
];

function statusColor(status: string): "green" | "amber" | "blue" {
  if (status.includes("Оплачено")) return "green";
  if (status.includes("Предоплат")) return "amber";
  return "blue";
}

type SortKey = "task" | "brand" | "date";

// kp_date is "DD.MM.YY" (backend serializers._fmt_date), not ISO — must
// parse before comparing, mirrors ActiveTasksPanel's parseDeadline.
function parseKpDate(s: string | null): number {
  if (!s) return Infinity; // nulls last regardless of direction
  const [d, m, y] = s.split(".").map(Number);
  return Date.UTC(2000 + y, m - 1, d);
}

export default function PaymentsPage() {
  const { data, isLoading } = usePayments();
  const { isEditor } = useAuth();
  const [formOpen, setFormOpen] = useState(false);
  const updateStatus = useUpdatePaymentStatus();
  const [sortKey, setSortKey] = useState<SortKey | null>(null);
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  }

  function sortArrow(key: SortKey) {
    if (sortKey !== key) return "";
    return sortDir === "asc" ? " ▲" : " ▼";
  }

  const rows = useMemo(() => {
    if (!data || !sortKey) return data ?? [];
    const sorted = [...data].sort((a, b) => {
      let cmp = 0;
      if (sortKey === "task") cmp = a.id.localeCompare(b.id, undefined, { numeric: true });
      else if (sortKey === "brand") cmp = a.brand.localeCompare(b.brand);
      else if (sortKey === "date") cmp = parseKpDate(a.kp_date) - parseKpDate(b.kp_date);
      return sortDir === "asc" ? cmp : -cmp;
    });
    return sorted;
  }, [data, sortKey, sortDir]);

  return (
    <div>
      {isEditor && (
        <div style={{ marginBottom: 14 }}>
          <Button variant="ghost" onClick={() => setFormOpen((o) => !o)}>
            {formOpen ? "Скрыть форму" : "+ Новое КП"}
          </Button>
          {formOpen && <NewPaymentForm onDone={() => setFormOpen(false)} />}
        </div>
      )}

      <Panel title="ОПЛАТЫ / КП" count={isLoading ? undefined : data?.length}>
        {isLoading ? (
          <p style={{ color: "var(--text3)", fontSize: 12 }}>Загрузка…</p>
        ) : !data || data.length === 0 ? (
          <p style={{ color: "var(--text3)", fontSize: 12 }}>Пока нет оплат</p>
        ) : (
          <table className={styles.table}>
            <thead>
              <tr>
                <th className={styles.sortable} onClick={() => toggleSort("task")}>
                  Задача{sortArrow("task")}
                </th>
                <th className={styles.sortable} onClick={() => toggleSort("brand")}>
                  Бренд{sortArrow("brand")}
                </th>
                <th>Подрядчик</th>
                <th className={styles.sortable} onClick={() => toggleSort("date")}>
                  Дата КП{sortArrow("date")}
                </th>
                <th>Образец</th>
                <th>Тираж</th>
                <th>Предоплата</th>
                <th>Баланс</th>
                <th>Статус</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((p) => (
                <tr key={p.id}>
                  <td>
                    <Badge color="gray">{p.id}</Badge>
                  </td>
                  <td>{p.brand}</td>
                  <td style={{ fontSize: 11 }}>{p.contractor}</td>
                  <td style={{ fontSize: 11, color: "var(--text3)" }}>
                    {p.kp_date || "—"}
                    {p.kp_doc_id && (
                      <>
                        {" · "}
                        <a
                          className={styles.link}
                          onClick={() =>
                            downloadFile(
                              `/api/documents/${p.kp_doc_id}/download`,
                              p.kp_doc_name ?? "kp",
                            )
                          }
                        >
                          📎 файл
                        </a>
                      </>
                    )}
                  </td>
                  <td>{p.sample}</td>
                  <td>{p.tirazh}</td>
                  <td style={{ color: "var(--accent3)" }}>{p.prepaid}</td>
                  <td style={{ color: p.balance === "0 ₽" ? "var(--accent3)" : "var(--warn)" }}>
                    {p.balance}
                  </td>
                  <td>
                    {isEditor ? (
                      <select
                        className={forms.select}
                        value={p.payment_status}
                        disabled={updateStatus.isPending}
                        onChange={(e) =>
                          updateStatus.mutate({ code: p.id, paymentStatus: e.target.value })
                        }
                        style={{ width: "auto" }}
                      >
                        {PAYMENT_STATUS_OPTIONS.map((o) => (
                          <option key={o.value} value={o.value}>
                            {o.label}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <Badge color={statusColor(p.status)}>{p.status}</Badge>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Panel>
    </div>
  );
}

function NewPaymentForm({ onDone }: { onDone: () => void }) {
  const upsert = useUpsertPayment();
  const [task, setTask] = useState("");
  const [contractor, setContractor] = useState("");
  const [sample, setSample] = useState("");
  const [tirazh, setTirazh] = useState("");
  const [prepaid, setPrepaid] = useState("");
  const [balance, setBalance] = useState("");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");

  function submit() {
    setError("");
    upsert.mutate(
      { task, contractor, currency: "RUB", sample, tirazh, prepaid, balance, status },
      {
        onSuccess: onDone,
        onError: (e) => setError(apiErrorMessage(e, "Не удалось сохранить оплату")),
      },
    );
  }

  return (
    <div className={forms.grid2} style={{ marginTop: 10 }}>
      <div className={forms.row}>
        <label className={forms.label}>Код задачи (RD-xxx)</label>
        <input className={forms.input} value={task} onChange={(e) => setTask(e.target.value)} />
      </div>
      <div className={forms.row}>
        <label className={forms.label}>Подрядчик</label>
        <input
          className={forms.input}
          value={contractor}
          onChange={(e) => setContractor(e.target.value)}
        />
      </div>
      <div className={forms.row}>
        <label className={forms.label}>Образец</label>
        <input className={forms.input} value={sample} onChange={(e) => setSample(e.target.value)} />
      </div>
      <div className={forms.row}>
        <label className={forms.label}>Тираж</label>
        <input className={forms.input} value={tirazh} onChange={(e) => setTirazh(e.target.value)} />
      </div>
      <div className={forms.row}>
        <label className={forms.label}>Предоплата</label>
        <input
          className={forms.input}
          value={prepaid}
          onChange={(e) => setPrepaid(e.target.value)}
        />
      </div>
      <div className={forms.row}>
        <label className={forms.label}>Баланс</label>
        <input
          className={forms.input}
          value={balance}
          onChange={(e) => setBalance(e.target.value)}
        />
      </div>
      <div className={forms.row} style={{ gridColumn: "1 / -1" }}>
        <label className={forms.label}>Статус</label>
        <input className={forms.input} value={status} onChange={(e) => setStatus(e.target.value)} />
      </div>
      <Button variant="primary" disabled={upsert.isPending || !task} onClick={submit}>
        Сохранить
      </Button>
      {error && (
        <div style={{ gridColumn: "1 / -1", color: "var(--danger)", fontSize: 11 }}>{error}</div>
      )}
    </div>
  );
}
