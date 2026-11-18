import { t } from "../../../i18n";
import { useState } from "react";

import { Badge } from "../../../components/Badge/Badge";
import { Button } from "../../../components/Button/Button";
import { NumberInput } from "../../../components/NumberInput/NumberInput";
import { canConfirmDeliveryRole, isEditorRole } from "../../../auth/roles";
import { useAuth } from "../../../auth/AuthContext";
import { apiErrorMessage } from "../../../api/client";
import {
  useDistributeTask,
  useTaskDeliveries,
  useUpdateDelivery,
} from "../../../api/queries/taskDetail";
import {
  DELIVERY_STATUS_COLOR,
  DELIVERY_STATUS_OPTIONS,
  deliveryStatusLabel,
  impliedQtyReceived,
} from "../../../lib/deliveryStatus";
import forms from "../../../styles/forms.module.css";
import styles from "./DeliveriesList.module.css";

/** ISO "2026-11-16" -> "16.11.26"; empty -> "—". */
function shortDate(iso: string | null | undefined): string {
  const m = iso ? /^(\d{4})-(\d{2})-(\d{2})/.exec(iso) : null;
  return m ? `${m[3]}.${m[2]}.${m[1].slice(2)}` : "—";
}

export function DeliveriesList({ code }: { code: string }) {
  const { data, isLoading } = useTaskDeliveries(code);
  const update = useUpdateDelivery(code);
  const distribute = useDistributeTask(code);
  const { user } = useAuth();
  const canConfirm = user ? canConfirmDeliveryRole(user.role) : false;
  const canDistribute = user ? isEditorRole(user.role) : false;
  const [count, setCount] = useState(30);
  const [error, setError] = useState("");

  if (isLoading) return <p style={{ fontSize: 12, color: "var(--text3)" }}>{t("Загрузка…")}</p>;
  const rows = data ?? [];

  async function handleDistribute() {
    setError("");
    try {
      await distribute.mutateAsync(count);
    } catch (e) {
      setError(apiErrorMessage(e, t("Не удалось распределить по ТТ")));
    }
  }

  if (rows.length === 0) {
    return (
      <div>
        <p style={{ fontSize: 12, color: "var(--text3)" }}>{t("Нет доставок по ТТ")}</p>
        {canDistribute && (
          <div style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 8 }}>
            <NumberInput
              className={forms.input}
              min={1}
              value={count}
              onChange={setCount}
              style={{ width: 70, marginBottom: 0, padding: "6px 8px" }}
            />
            <Button variant="ghost" disabled={distribute.isPending} onClick={handleDistribute}>
              {t("Распределить по ТТ")}
            </Button>
            {error && <span style={{ fontSize: 11, color: "var(--danger)" }}>{error}</span>}
          </div>
        )}
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      {rows.map((d) => (
        <div key={d.id} className={styles.row}>
          <span className={styles.name}>
            {d.point_name} <span className={styles.city}>· {d.city}</span>
          </span>
          <span className={styles.qty}>
            {d.qty_received}/{d.qty_expected}
          </span>
          <div className={styles.controls}>
            {canConfirm ? (
              <label className={styles.dateField} title={t("Дата прихода в ТТ")}>
                <span
                  className={`${forms.input} ${styles.dateLabel} ${d.arrival_date ? "" : styles.dateLabelEmpty}`}
                >
                  {shortDate(d.arrival_date)}
                </span>
                <input
                  className={styles.dateInput}
                  type="date"
                  aria-label={t("Дата прихода в ТТ")}
                  value={d.arrival_date ?? ""}
                  disabled={update.isPending}
                  onClick={(e) => {
                    // Desktop browsers don't open the picker on a click into an
                    // invisible input's text area — open it explicitly.
                    try {
                      e.currentTarget.showPicker?.();
                    } catch {
                      /* not supported / not user-activated: native fallback */
                    }
                  }}
                  onChange={(e) =>
                    update.mutate({ id: d.id, payload: { arrival_date: e.target.value || null } })
                  }
                />
              </label>
            ) : (
              <span style={{ color: "var(--text3)", fontSize: 11 }} title={t("Дата прихода в ТТ")}>
                {shortDate(d.arrival_date)}
              </span>
            )}
            {canConfirm ? (
              <select
                className={`${forms.select} ${styles.status}`}
                value={d.status}
                disabled={update.isPending}
                onChange={(e) => {
                  const status = e.target.value;
                  const qty_received = impliedQtyReceived(status, d.qty_expected);
                  update.mutate({ id: d.id, payload: { status, qty_received } });
                }}
              >
                {DELIVERY_STATUS_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            ) : (
              <Badge color={DELIVERY_STATUS_COLOR[d.status] ?? "gray"}>
                {deliveryStatusLabel(d.status)}
              </Badge>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
