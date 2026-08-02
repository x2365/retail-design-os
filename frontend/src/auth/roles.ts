/** Mirrors backend/app/models/enums.py Role. The API types this as a plain
 * `string` (Pydantic schema uses `role: str`), so we re-assert the closed
 * set here for exhaustive checks in the UI. */
export type Role = "admin" | "manager" | "brand" | "retailer" | "shipment_manager" | "viewer";

export const ROLE_LABELS: Record<Role, string> = {
  admin: "Администратор",
  manager: "Менеджер",
  brand: "Бренд",
  retailer: "Ритейлер",
  shipment_manager: "Отдел отгрузки",
  viewer: "Наблюдатель",
};

/** admin/manager may create/edit most resources — mirrors isEditor() in the
 * old frontend and security.require_roles(Role.manager) on the backend
 * (which always additionally allows admin). */
export function isEditorRole(role: string): boolean {
  return role === "admin" || role === "manager";
}

/** Roles allowed to confirm a delivery's status at a retail point (mirrors
 * WriteDep-equivalent checks in routers/deliveries.py's business rule). */
export function canConfirmDeliveryRole(role: string): boolean {
  return (
    role === "admin" || role === "manager" || role === "retailer" || role === "shipment_manager"
  );
}
