import { Badge } from "../../../components/Badge/Badge";
import { canConfirmDeliveryRole } from "../../../auth/roles";
import { useAuth } from "../../../auth/AuthContext";
import { useTaskDeliveries, useUpdateDelivery } from "../../../api/queries/taskDetail";
import {
  DELIVERY_STATUS_COLOR,
  DELIVERY_STATUS_OPTIONS,
  deliveryStatusLabel,
  impliedQtyReceived,
} from "../../../lib/deliveryStatus";

export function DeliveriesList({ code }: { code: string }) {
  const { data, isLoading } = useTaskDeliveries(code);
  const update = useUpdateDelivery(code);
  const { user } = useAuth();
  const canConfirm = user ? canConfirmDeliveryRole(user.role) : false;

  if (isLoading) return <p style={{ fontSize: 12, color: "var(--text3)" }}>Загрузка…</p>;
  const rows = data ?? [];
  if (rows.length === 0)
    return <p style={{ fontSize: 12, color: "var(--text3)" }}>Нет доставок по ТТ</p>;

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
            <select
              value={d.status}
              disabled={update.isPending}
              onChange={(e) => {
                const status = e.target.value;
                const qty_received = impliedQtyReceived(status, d.qty_expected);
                update.mutate({ id: d.id, payload: { status, qty_received } });
              }}
              style={{ fontSize: 11 }}
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
