import { useState } from "react";

import { Button } from "../../components/Button/Button";
import { Modal } from "../../components/Modal/Modal";
import { NumberInput } from "../../components/NumberInput/NumberInput";
import { apiErrorMessage } from "../../api/client";
import { useBrands } from "../../api/queries/brands";
import { useCreateEquipment, useUpdateEquipment } from "../../api/queries/equipment";
import type { components } from "../../api/schema";
import forms from "../../styles/forms.module.css";
import { KIND_OPTIONS } from "./kindLabels";

type Equipment = components["schemas"]["EquipmentOut"];

export function EquipmentFormModal({
  equipment,
  onClose,
}: {
  equipment: Equipment | null;
  onClose: () => void;
}) {
  const { data: brands } = useBrands();
  // Not `useState(equipment?.brand ?? brands?.[0]?.name ?? "")`: brands is
  // still loading on first render (useState's initializer only runs once),
  // so that would permanently lock `brand` to "" and fail EquipmentCreate's
  // min_length=1 on submit. Falling back at read-time instead stays correct
  // once the brands query resolves.
  const [brand, setBrand] = useState(equipment?.brand ?? "");
  const effectiveBrand = brand || brands?.[0]?.name || "";
  const [name, setName] = useState(equipment?.name ?? "");
  const [kind, setKind] = useState(equipment?.kind ?? "stand");
  const [dimensions, setDimensions] = useState(equipment?.dimensions ?? "");
  const [description, setDescription] = useState(equipment?.description ?? "");
  const [budget, setBudget] = useState(equipment ? Math.round(equipment.est_budget / 100) : 0);
  const [sample, setSample] = useState(equipment ? Math.round(equipment.est_sample / 100) : 0);
  const [tirazh, setTirazh] = useState(equipment ? Math.round(equipment.est_tirazh / 100) : 0);
  const [error, setError] = useState("");
  const create = useCreateEquipment();
  const update = useUpdateEquipment();
  const pending = create.isPending || update.isPending;

  function submit() {
    setError("");
    const onError = (e: unknown) => setError(apiErrorMessage(e, "Не удалось сохранить изделие"));
    const common = {
      name,
      kind,
      dimensions,
      description,
      est_budget: budget * 100,
      est_sample: sample * 100,
      est_tirazh: tirazh * 100,
    };
    if (equipment) {
      update.mutate({ id: equipment.id, payload: common }, { onSuccess: onClose, onError });
    } else {
      create.mutate(
        { ...common, brand: effectiveBrand, currency: "RUB" },
        { onSuccess: onClose, onError },
      );
    }
  }

  return (
    <Modal title={equipment ? "Изменить изделие" : "Новое изделие"} onClose={onClose}>
      {!equipment && (
        <div className={forms.row}>
          <label className={forms.label}>Бренд</label>
          <select
            className={forms.select}
            value={effectiveBrand}
            onChange={(e) => setBrand(e.target.value)}
          >
            {(brands ?? []).map((b) => (
              <option key={b.id} value={b.name}>
                {b.name} (Гр.{b.group})
              </option>
            ))}
          </select>
        </div>
      )}
      <div className={forms.row}>
        <label className={forms.label}>Название</label>
        <input className={forms.input} value={name} onChange={(e) => setName(e.target.value)} />
      </div>
      <div className={forms.grid2}>
        <div className={forms.row}>
          <label className={forms.label}>Тип</label>
          <select className={forms.select} value={kind} onChange={(e) => setKind(e.target.value)}>
            {KIND_OPTIONS.map((k) => (
              <option key={k.value} value={k.value}>
                {k.label}
              </option>
            ))}
          </select>
        </div>
        <div className={forms.row}>
          <label className={forms.label}>Размеры</label>
          <input
            className={forms.input}
            value={dimensions}
            onChange={(e) => setDimensions(e.target.value)}
          />
        </div>
      </div>
      <div className={forms.row}>
        <label className={forms.label}>Описание</label>
        <textarea
          className={forms.textarea}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
      </div>
      <div className={forms.grid2}>
        <div className={forms.row}>
          <label className={forms.label}>Бюджет, ₽</label>
          <NumberInput className={forms.input} value={budget} onChange={setBudget} />
        </div>
        <div className={forms.row}>
          <label className={forms.label}>Образец, ₽</label>
          <NumberInput className={forms.input} value={sample} onChange={setSample} />
        </div>
      </div>
      <div className={forms.row}>
        <label className={forms.label}>Тираж, ₽</label>
        <NumberInput className={forms.input} value={tirazh} onChange={setTirazh} />
      </div>
      <div className={forms.error}>{error}</div>
      <Button variant="primary" disabled={pending || !name.trim()} onClick={submit}>
        Сохранить
      </Button>
    </Modal>
  );
}
