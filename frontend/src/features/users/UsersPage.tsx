import { useState } from "react";

import { Badge } from "../../components/Badge/Badge";
import { Button } from "../../components/Button/Button";
import { Panel } from "../../components/Panel/Panel";
import { apiErrorMessage } from "../../api/client";
import {
  useCreateUser,
  useResetUserPassword,
  useUpdateUser,
  useUsers,
} from "../../api/queries/users";
import { ROLE_LABELS, type Role } from "../../auth/roles";
import forms from "../../styles/forms.module.css";
import { PasswordModal } from "./PasswordModal";
import styles from "./UsersPage.module.css";

const ROLES = Object.keys(ROLE_LABELS) as Role[];

export default function UsersPage() {
  const { data, isLoading } = useUsers();
  const createUser = useCreateUser();
  const updateUser = useUpdateUser();
  const resetPassword = useResetUserPassword();
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState<Role>("viewer");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [resetTarget, setResetTarget] = useState<{ id: number; email: string } | null>(null);

  function submitNewUser() {
    setError("");
    if (!email || !fullName || password.length < 6) {
      setError("Заполните email, ФИО и пароль (мин. 6 символов)");
      return;
    }
    createUser.mutate(
      { email, full_name: fullName, role, password },
      {
        onSuccess: () => {
          setEmail("");
          setFullName("");
          setPassword("");
        },
        onError: (e) => setError(apiErrorMessage(e, "Не удалось создать пользователя")),
      },
    );
  }

  return (
    <Panel title="ПОЛЬЗОВАТЕЛИ">
      {resetTarget && (
        <PasswordModal
          title={`Новый пароль для ${resetTarget.email}`}
          onSubmit={({ newPassword }) =>
            resetPassword.mutateAsync({ id: resetTarget.id, newPassword })
          }
          onClose={() => setResetTarget(null)}
        />
      )}

      <div className={styles.newRow}>
        <input
          className={forms.input}
          style={{ marginBottom: 0, width: 190 }}
          placeholder="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <input
          className={forms.input}
          style={{ marginBottom: 0, width: 180 }}
          placeholder="ФИО"
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
        />
        <select
          className={forms.select}
          style={{ width: "auto" }}
          value={role}
          onChange={(e) => setRole(e.target.value as Role)}
        >
          {ROLES.map((r) => (
            <option key={r} value={r}>
              {ROLE_LABELS[r]}
            </option>
          ))}
        </select>
        <input
          className={forms.input}
          style={{ marginBottom: 0, width: 150 }}
          placeholder="пароль (мин. 6)"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <Button variant="primary" disabled={createUser.isPending} onClick={submitNewUser}>
          + Добавить
        </Button>
      </div>
      {error && <div className={forms.error}>{error}</div>}

      {isLoading ? (
        <p style={{ color: "var(--text3)", fontSize: 12 }}>Загрузка…</p>
      ) : (
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Email</th>
              <th>ФИО</th>
              <th>Роль</th>
              <th>Статус</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {(data ?? []).map((u) => (
              <tr key={u.id}>
                <td>{u.email}</td>
                <td>{u.full_name}</td>
                <td>
                  <select
                    className={forms.select}
                    style={{ width: "auto" }}
                    value={u.role}
                    onChange={(e) =>
                      updateUser.mutate({ id: u.id, payload: { role: e.target.value } })
                    }
                  >
                    {ROLES.map((r) => (
                      <option key={r} value={r}>
                        {ROLE_LABELS[r]}
                      </option>
                    ))}
                  </select>
                </td>
                <td>
                  <Badge color={u.is_active ? "green" : "gray"}>
                    {u.is_active ? "активен" : "отключён"}
                  </Badge>
                </td>
                <td style={{ textAlign: "right", whiteSpace: "nowrap" }}>
                  <button
                    className={styles.link}
                    onClick={() => setResetTarget({ id: u.id, email: u.email })}
                  >
                    Сброс пароля
                  </button>
                  {"  "}
                  <button
                    className={styles.link}
                    onClick={() =>
                      updateUser.mutate({ id: u.id, payload: { is_active: !u.is_active } })
                    }
                  >
                    {u.is_active ? "Отключить" : "Включить"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Panel>
  );
}
