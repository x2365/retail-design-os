import { useState } from "react";

import { Button } from "../../components/Button/Button";
import { Modal } from "../../components/Modal/Modal";
import { apiErrorMessage } from "../../api/client";
import forms from "../../styles/forms.module.css";

interface PasswordModalProps {
  title: string;
  requireCurrent?: boolean;
  onSubmit: (args: { currentPassword?: string; newPassword: string }) => Promise<void>;
  onClose: () => void;
}

/** Shared shell for both "reset a user's password" (admin) and "change my
 * password" (self) — same fields, different submit handler + role. */
export function PasswordModal({ title, requireCurrent, onSubmit, onClose }: PasswordModalProps) {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  async function submit() {
    setError("");
    if (next.length < 6) {
      setError("Пароль должен быть не короче 6 символов");
      return;
    }
    setPending(true);
    try {
      await onSubmit({ currentPassword: current || undefined, newPassword: next });
      onClose();
    } catch (e) {
      setError(apiErrorMessage(e, "Не удалось сменить пароль"));
    } finally {
      setPending(false);
    }
  }

  return (
    <Modal title={title} onClose={onClose}>
      {requireCurrent && (
        <div className={forms.row}>
          <label className={forms.label}>Текущий пароль</label>
          <input
            type="password"
            className={forms.input}
            value={current}
            onChange={(e) => setCurrent(e.target.value)}
          />
        </div>
      )}
      <div className={forms.row}>
        <label className={forms.label}>Новый пароль (мин. 6 символов)</label>
        <input
          type="password"
          className={forms.input}
          value={next}
          onChange={(e) => setNext(e.target.value)}
        />
      </div>
      <div className={forms.error}>{error}</div>
      <Button variant="primary" disabled={pending} onClick={submit}>
        Сохранить
      </Button>
    </Modal>
  );
}
