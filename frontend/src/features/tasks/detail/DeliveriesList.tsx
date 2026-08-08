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

export function DeliveriesList({ code }: { code: string }) {
  const { data, isLoading } = useTaskDeliveries(code);
  const update = useUpdateDelivery(code);
  const distribute = useDistributeTask(code);
  const { user } = useAuth();
  const canConfirm = user ? canConfirmDeliveryRole(user.role) : false;
  const canDistribute = user ? isEditorRole(user.role) : false;
  const [count, setCount] = useState(30);
  const [error, setError] = useState("");

  if (isLoading) return <p style={{ fontSize: 12, color: "var(--text3)" }}>Загрузка…</p>;
  const rows = data ?? [];

  async function handleDistribute() {
    setError("");
    try {
      await distribute.mutateAsync(count);
    } catch (e) {
      setError(apiErrorMessage(e, "Не удалось распределить по ТТ"));
    }
  }

  if (rows.length === 0) {
    return (
      <div>
        <p style={{ fontSize: 12, color: "var(--text3)" }}>Нет доставок по ТТ</p>
        {canDistribute && (
          <div style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 8 }}>
            <NumberInput
              className={forms.input}
              min={1}
              value={count}
              onChange={setCount}
              style={{ width: 70, marginBottom: 0, padding: "6px 8px", fontSize: 12 }}
            />
            <Button variant="ghost" disabled={distribute.isPending} onClick={handleDistribute}>
              Распределить по ТТ
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
        <div key={d.id} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12 }}>
          <span style={{ flex: 1 }}>
            {d.point_name} <span style={{ color: "var(--text3)" }}>· {d.city}</span>
          </span>
          <span style={{ color: "var(--text3)" }}>
            {d.qty_received}/{d.qty_expected}
          </span>
          {canConfirm ? (
            <input
              className={forms.input}
              type="date"
              title="Дата прихода в ТТ"
              value={d.arrival_date ?? ""}
              disabled={update.isPending}
              onChange={(e) =>
                update.mutate({ id: d.id, payload: { arrival_date: e.target.value || null } })
              }
              style={{ width: "auto", marginBottom: 0, padding: "4px 8px", fontSize: 11 }}
            />
          ) : (
            <span style={{ color: "var(--text3)", fontSize: 11 }} title="Дата прихода в ТТ">
              {d.arrival_date ?? "—"}
            </span>
          )}
          {canConfirm ? (
            <select
              className={forms.select}
              value={d.status}
              disabled={update.isPending}
              onChange={(e) => {
                const status = e.target.value;
                const qty_received = impliedQtyReceived(status, d.qty_expected);
                update.mutate({ id: d.id, payload: { status, qty_received } });
              }}
              style={{ width: "auto", fontSize: 11 }}
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
      ))}
    </div>
  );
}
