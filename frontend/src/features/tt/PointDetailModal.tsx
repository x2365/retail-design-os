import { t, tServer } from "../../i18n";
import { Badge } from "../../components/Badge/Badge";
import { Modal } from "../../components/Modal/Modal";
import { useAuth } from "../../auth/AuthContext";
import { canConfirmDeliveryRole } from "../../auth/roles";
import { usePointDeliveries, useUpdatePointDelivery } from "../../api/queries/retailPoints";
import {
  DELIVERY_STATUS_OPTIONS as STATUS_OPTIONS,
  impliedQtyReceived,
} from "../../lib/deliveryStatus";
import styles from "./PointDetailModal.module.css";

const REGION_OPTIONS: { value: string; label: string }[] = [
  { value: "local", label: t("Локально") },
  { value: "rc", label: t("РЦ") },
  { value: "cis", label: t("СНГ") },
  { value: "middle_east", label: "Middle East" },
];

interface PointDetailModalProps {
  point: { id: number; name: string; code: string; city: string; address: string };
  onClose: () => void;
}

export function PointDetailModal({ point, onClose }: PointDetailModalProps) {
  const { data, isLoading } = usePointDeliveries(point.id);
  const update = useUpdatePointDelivery(point.id);
  const { user } = useAuth();
  const canConfirm = user ? canConfirmDeliveryRole(user.role) : false;

  return (
    <Modal
      title={point.name}
      sub={`${point.code} · ${point.city} · ${point.address}`}
      onClose={onClose}
    >
      {isLoading ? (
        <p style={{ color: "var(--text3)", fontSize: 12 }}>{t("Загрузка…")}</p>
      ) : !data || data.length === 0 ? (
        <p style={{ color: "var(--text3)", fontSize: 12 }}>
          {t("В эту точку пока ничего не отгружено")}
        </p>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              <th
                style={{
                  textAlign: "left",
                  fontSize: 10,
                  color: "var(--text3)",
                  padding: "6px 8px",
                }}
              >
                {t("Задача")}
              </th>
              <th
                style={{
                  textAlign: "left",
                  fontSize: 10,
                  color: "var(--text3)",
                  padding: "6px 8px",
                }}
              >
                {t("Изделие")}
              </th>
              <th
                style={{
                  textAlign: "left",
                  fontSize: 10,
                  color: "var(--text3)",
                  padding: "6px 8px",
                }}
              >
                {t("Статус")}
              </th>
              <th
                style={{
                  textAlign: "left",
                  fontSize: 10,
                  color: "var(--text3)",
                  padding: "6px 8px",
                }}
              >
                {t("Регион")}
              </th>
              <th
                style={{
                  textAlign: "left",
                  fontSize: 10,
                  color: "var(--text3)",
                  padding: "6px 8px",
                }}
              >
                {t("Кол-во")}
              </th>
            </tr>
          </thead>
          <tbody>
            {data.map((d) => (
              <tr key={d.id} style={{ borderBottom: "1px solid var(--border)" }}>
                <td style={{ padding: "8px" }}>
                  <Badge color="gray">{d.task}</Badge>
                </td>
                <td style={{ padding: "8px", fontSize: 12 }}>{d.equipment || d.task_name}</td>
                <td style={{ padding: "8px" }}>
                  {canConfirm ? (
                    <select
                      className={styles.select}
                      value={d.status}
                      onChange={(e) => {
                        const status = e.target.value;
                        const qty_received = impliedQtyReceived(status, d.qty_expected);
                        update.mutate({ id: d.id, payload: { status, qty_received } });
                      }}
                    >
                      {STATUS_OPTIONS.map((o) => (
                        <option key={o.value} value={o.value}>
                          {o.label}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <span style={{ fontSize: 12 }}>
                      {STATUS_OPTIONS.find((o) => o.value === d.status)?.label ?? d.status}
                    </span>
                  )}
                </td>
                <td style={{ padding: "8px" }}>
                  {canConfirm ? (
                    <select
                      className={styles.select}
                      value={d.region}
                      onChange={(e) =>
                        update.mutate({ id: d.id, payload: { region: e.target.value } })
                      }
                    >
                      {REGION_OPTIONS.map((o) => (
                        <option key={o.value} value={o.value}>
                          {o.label}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <Badge color="gray">{tServer(d.region_label)}</Badge>
                  )}
                </td>
                <td style={{ padding: "8px", fontSize: 12 }}>
                  {d.qty_received}/{d.qty_expected}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Modal>
  );
}
