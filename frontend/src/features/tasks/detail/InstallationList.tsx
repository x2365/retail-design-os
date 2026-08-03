import { Badge } from "../../../components/Badge/Badge";
import { canConfirmDeliveryRole } from "../../../auth/roles";
import { useAuth } from "../../../auth/AuthContext";
import { useTaskDeliveries, useUpdateDelivery } from "../../../api/queries/taskDetail";

/** Stage 10 "Монтаж" — distinct from stage 9 "Доставка": a delivery arriving
 * at a retail point and someone actually installing it there are different
 * real-world events. Installation can only be confirmed once the delivery
 * itself is marked delivered (enforced by the backend). */
export function InstallationList({ code }: { code: string }) {
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
      {rows.map((d) => {
        const canInstall = d.status === "delivered";
        return (
          <div key={d.id} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12 }}>
            <span style={{ flex: 1 }}>
              {d.point_name} <span style={{ color: "var(--text3)" }}>· {d.city}</span>
            </span>
            {d.installed_at ? (
              <Badge color="green">
                ✓ Смонтировано{d.installed_by ? ` · ${d.installed_by}` : ""}
              </Badge>
            ) : !canInstall ? (
              <Badge color="gray">сначала доставка</Badge>
            ) : canConfirm ? (
              <button
                style={{
                  background: "none",
                  border: "none",
                  color: "var(--accent)",
                  fontSize: 11,
                  cursor: "pointer",
                }}
                disabled={update.isPending}
                onClick={() => update.mutate({ id: d.id, payload: { installed: true } })}
              >
                отметить монтаж
              </button>
            ) : (
              <Badge color="amber">ожидает монтажа</Badge>
            )}
          </div>
        );
      })}
    </div>
  );
}
