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

/** Who owns which approval gate (prep-/kp-/sample-approval) — mirrors
 * _check_gate_role in routers/tasks.py. admin/manager may always decide any
 * gate; "brand" only its brand sign-off, "retailer" only the retail-chain
 * sign-off ("zya"/"network" are the same real-world actor at different
 * stages). Gate `""` (sample-approval's legacy "approve all three at once")
 * is manager/admin-only. */
export function canApproveGate(role: string | undefined, gate: string): boolean {
  if (!role) return false;
  if (role === "admin" || role === "manager") return true;
  if (role === "brand") return gate === "brand" || gate === "director";
  if (role === "retailer") return gate === "zya" || gate === "network";
  return false;
}
