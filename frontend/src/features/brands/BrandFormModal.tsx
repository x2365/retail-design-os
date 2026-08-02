import { useState } from "react";

import { Button } from "../../components/Button/Button";
import { Modal } from "../../components/Modal/Modal";
import { apiErrorMessage } from "../../api/client";
import { useCreateBrand, useUpdateBrand } from "../../api/queries/brands";
import forms from "../../styles/forms.module.css";

interface BrandFormModalProps {
  brand?: { id: number; name: string } | null;
  groupCode: string;
  onClose: () => void;
}

export function BrandFormModal({ brand, groupCode, onClose }: BrandFormModalProps) {
  const [name, setName] = useState(brand?.name ?? "");
  const [error, setError] = useState("");
  const create = useCreateBrand();
  const update = useUpdateBrand();
  const pending = create.isPending || update.isPending;

  function submit() {
    setError("");
    const onError = (e: unknown) => setError(apiErrorMessage(e, "Не удалось сохранить бренд"));
    if (brand) {
      update.mutate({ id: brand.id, payload: { name } }, { onSuccess: onClose, onError });
    } else {
      create.mutate({ name, group: groupCode }, { onSuccess: onClose, onError });
    }
  }

  return (
    <Modal
      title={brand ? "Изменить бренд" : "Новый бренд"}
      sub={`Группа ${groupCode}`}
      onClose={onClose}
    >
      <div className={forms.row}>
        <label className={forms.label}>Название</label>
        <input
          className={forms.input}
          value={name}
          onChange={(e) => setName(e.target.value)}
          autoFocus
        />
      </div>
      <div className={forms.error}>{error}</div>
      <Button variant="primary" disabled={pending || !name.trim()} onClick={submit}>
        Сохранить
      </Button>
    </Modal>
  );
}
