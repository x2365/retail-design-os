/** Single source of truth for delivery status options — shared by the task
 * detail modal's DeliveriesList and the retail point's PointDetailModal, so
 * the same Delivery can be moved through the same states from either screen
 * instead of each surface having its own narrower, inconsistent copy. */
export const DELIVERY_STATUS_OPTIONS: { value: string; label: string }[] = [
  { value: "pending", label: "Ожидает отгрузки" },
  { value: "delivered", label: "✓ Получено" },
  { value: "partial", label: "~ Неполный объём" },
  { value: "missing", label: "✗ Не получено" },
];

export const DELIVERY_STATUS_COLOR: Record<string, "green" | "amber" | "red" | "gray"> = {
  pending: "gray",
  delivered: "green",
  partial: "amber",
  missing: "red",
};

export function deliveryStatusLabel(status: string): string {
  return DELIVERY_STATUS_OPTIONS.find((o) => o.value === status)?.label ?? status;
}

/** qty_received to send alongside a status change: full for delivered, zero
 * for missing/pending, left untouched (undefined -> omitted from the PATCH
 * body) for partial, where the actual received quantity has to be entered
 * separately. */
export function impliedQtyReceived(status: string, qtyExpected: number): number | undefined {
  if (status === "delivered") return qtyExpected;
  if (status === "missing" || status === "pending") return 0;
  return undefined;
}
