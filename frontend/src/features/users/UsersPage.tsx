import { locale, t, tServer } from "../../i18n";
import { useState } from "react";

import { Badge } from "../../components/Badge/Badge";
import { Button } from "../../components/Button/Button";
import { Panel } from "../../components/Panel/Panel";
import { apiErrorMessage } from "../../api/client";
import { useRestoreSnapshot, useSnapshot, useTakeSnapshot } from "../../api/queries/snapshot";
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

function formatTakenAt(iso: string): string {
  return new Date(iso).toLocaleString(locale, {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function SnapshotPanel() {
  const { data: snap, isLoading } = useSnapshot();
  const takeSnapshot = useTakeSnapshot();
  const restoreSnapshot = useRestoreSnapshot();
  const [error, setError] = useState("");

  function onTake() {
    setError("");
    takeSnapshot.mutate(undefined, {
      onError: (e) => setError(apiErrorMessage(e, t("Не удалось сохранить точку сброса"))),
    });
  }

  function onRestore() {
    setError("");
    if (
      !confirm(
        t(
          "Откатить все данные к последней сохранённой точке сброса? Всё, что накопилось после неё, будет безвозвратно потеряно.",
        ),
      )
    )
      return;
    restoreSnapshot.mutate(undefined, {
      onError: (e) => setError(apiErrorMessage(e, t("Не удалось выполнить сброс"))),
    });
  }

  return (
    <Panel title={t("ДЕМО-ДАННЫЕ")}>
      <p style={{ fontSize: 12, color: "var(--text2)", marginBottom: 10 }}>
        {t(
          "Точка сброса — снимок всей базы, к которому можно откатить накопившиеся правки посетителей демо. Внешний cron дёргает это же по расписанию (см. render.yaml).",
        )}
      </p>
      {isLoading ? (
        <p style={{ fontSize: 12, color: "var(--text3)" }}>{t("Загрузка…")}</p>
      ) : (
        <p style={{ fontSize: 12, color: "var(--text3)", marginBottom: 10 }}>
          {snap?.taken_at
            ? t("Сохранена: {at} ({kb} КБ)", {
                at: formatTakenAt(snap.taken_at),
                kb: Math.round((snap.size_bytes ?? 0) / 1024),
              })
            : t("Точка сброса ещё не сохранена")}
        </p>
      )}
      <div style={{ display: "flex", gap: 8 }}>
        <Button variant="ghost" disabled={takeSnapshot.isPending} onClick={onTake}>
          {t("Сохранить точку сброса")}
        </Button>
        <Button
          variant="ghost"
          disabled={restoreSnapshot.isPending || !snap?.taken_at}
          onClick={onRestore}
        >
          {t("Сбросить сейчас")}
        </Button>
      </div>
      {error && <div className={forms.error}>{error}</div>}
    </Panel>
  );
}

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
      setError(t("Заполните email, ФИО и пароль (мин. 6 символов)"));
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
        onError: (e) => setError(apiErrorMessage(e, t("Не удалось создать пользователя"))),
      },
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <SnapshotPanel />
      <Panel title={t("ПОЛЬЗОВАТЕЛИ")}>
        {resetTarget && (
          <PasswordModal
            title={t("Новый пароль для {email}", { email: resetTarget.email })}
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
            placeholder={t("ФИО")}
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
            placeholder={t("пароль (мин. 6)")}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <Button variant="primary" disabled={createUser.isPending} onClick={submitNewUser}>
            {t("+ Добавить")}
          </Button>
        </div>
        {error && <div className={forms.error}>{error}</div>}

        {isLoading ? (
          <p style={{ color: "var(--text3)", fontSize: 12 }}>{t("Загрузка…")}</p>
        ) : (
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Email</th>
                <th>{t("ФИО")}</th>
                <th>{t("Роль")}</th>
                <th>{t("Статус")}</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {(data ?? []).map((u) => (
                <tr key={u.id}>
                  <td>{u.email}</td>
                  <td>{tServer(u.full_name)}</td>
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
                      {u.is_active ? t("активен") : t("отключён")}
                    </Badge>
                  </td>
                  <td style={{ textAlign: "right", whiteSpace: "nowrap" }}>
                    <button
                      className={styles.link}
                      onClick={() => setResetTarget({ id: u.id, email: u.email })}
                    >
                      {t("Сброс пароля")}
                    </button>
                    {"  "}
                    <button
                      className={styles.link}
                      onClick={() =>
                        updateUser.mutate({ id: u.id, payload: { is_active: !u.is_active } })
                      }
                    >
                      {u.is_active ? t("Отключить") : t("Включить")}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Panel>
    </div>
  );
}
