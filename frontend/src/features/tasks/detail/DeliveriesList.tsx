import { Badge } from "../../../components/Badge/Badge";
import { canConfirmDeliveryRole } from "../../../auth/roles";
import { useAuth } from "../../../auth/AuthContext";
import { useTaskDeliveries, useUpdateDelivery } from "../../../api/queries/taskDetail";

const STATUS_RU: Record<string, string> = {
  pending: "Ожидает",
  delivered: "Получено",
  partial: "Есть брак",
  missing: "Не получено",
};
const STATUS_COLOR: Record<string, "green" | "amber" | "red" | "gray"> = {
  pending: "gray",
  delivered: "green",
  partial: "amber",
  missing: "red",
};

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
          <Badge color={STATUS_COLOR[d.status] ?? "gray"}>{STATUS_RU[d.status] ?? d.status}</Badge>
          {canConfirm && d.status !== "delivered" && (
            <button
              style={{
                background: "none",
                border: "none",
                color: "var(--accent)",
                fontSize: 11,
                cursor: "pointer",
              }}
              disabled={update.isPending}
              onClick={() => update.mutate({ id: d.id, status: "delivered" })}
            >
              подтвердить
            </button>
          )}
        </div>
      ))}
    </div>
  );
}
