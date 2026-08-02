import { useState } from "react";

import { Button } from "../../components/Button/Button";
import { Modal } from "../../components/Modal/Modal";
import { apiErrorMessage } from "../../api/client";
import { useCreatePoint, useUpdatePoint } from "../../api/queries/retailPoints";
import forms from "../../styles/forms.module.css";

interface PointFormModalProps {
  point?: { id: number; name: string; city: string; address: string } | null;
  onClose: () => void;
}

/** Add/edit form for a retail point — replaces the old app's three chained
 * browser prompt() dialogs with a proper inline form. */
export function PointFormModal({ point, onClose }: PointFormModalProps) {
  const [name, setName] = useState(point?.name ?? "");
  const [city, setCity] = useState(point?.city ?? "");
  const [address, setAddress] = useState(point?.address ?? "");
  const [error, setError] = useState("");
  const create = useCreatePoint();
  const update = useUpdatePoint();
  const pending = create.isPending || update.isPending;

  function submit() {
    setError("");
    const onError = (e: unknown) => setError(apiErrorMessage(e, "Не удалось сохранить точку"));
    if (point) {
      update.mutate(
        { id: point.id, payload: { name, city, address } },
        { onSuccess: onClose, onError },
      );
    } else {
      create.mutate({ name, city, address }, { onSuccess: onClose, onError });
    }
  }

  return (
    <Modal title={point ? "Изменить точку" : "Новая торговая точка"} onClose={onClose}>
      <div className={forms.row}>
        <label className={forms.label}>Название</label>
        <input className={forms.input} value={name} onChange={(e) => setName(e.target.value)} />
      </div>
      <div className={forms.grid2}>
        <div className={forms.row}>
          <label className={forms.label}>Город</label>
          <input className={forms.input} value={city} onChange={(e) => setCity(e.target.value)} />
        </div>
        <div className={forms.row}>
          <label className={forms.label}>Адрес</label>
          <input
            className={forms.input}
            value={address}
            onChange={(e) => setAddress(e.target.value)}
          />
        </div>
      </div>
      <div className={forms.error}>{error}</div>
      <Button variant="primary" disabled={pending || !name.trim()} onClick={submit}>
        Сохранить
      </Button>
    </Modal>
  );
}
