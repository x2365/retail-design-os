import type { ReactNode } from "react";

import { useAuth } from "../auth/AuthContext";
import type { Role } from "../auth/roles";

/** Gates a route (or any subtree) to specific roles. The backend is the real
 * enforcement point (403s otherwise) — this only avoids showing a dead end
 * for roles that can never use the page, mirroring the old app's
 * `nav-users` visibility check. */
export function RequireRole({ roles, children }: { roles: Role[]; children: ReactNode }) {
  const { user } = useAuth();
  if (!user || !roles.includes(user.role as Role)) {
    return (
      <p style={{ color: "var(--text2)", fontSize: 13 }}>
        Доступно только для роли: {roles.join(", ")}.
      </p>
    );
  }
  return <>{children}</>;
}
