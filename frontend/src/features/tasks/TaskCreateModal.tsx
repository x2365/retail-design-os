import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { Button } from "../../components/Button/Button";
import { Modal } from "../../components/Modal/Modal";
import { apiErrorMessage } from "../../api/client";
import { useBrands } from "../../api/queries/brands";
import { useCreateTask } from "../../api/queries/tasks";
import forms from "../../styles/forms.module.css";

export function TaskCreateModal({ onClose }: { onClose: () => void }) {
  const navigate = useNavigate();
  const { data: brands } = useBrands();
  // Same brand-fallback pattern as EquipmentFormModal: brands is still
  // loading on first render, so falling back at read-time (not in the
  // useState initializer) is what keeps `brand` correct once it resolves.
  const [brand, setBrand] = useState("");
  const effectiveBrand = brand || brands?.[0]?.name || "";
  const [name, setName] = useState("");
  const [deadline, setDeadline] = useState("");
  const [launch, setLaunch] = useState("");
  const [error, setError] = useState("");
  const create = useCreateTask();

  function submit() {
    setError("");
    create.mutate(
      {
        name,
        brand: effectiveBrand,
        deadline: deadline || undefined,
        launch: launch || undefined,
        stage: 1,
        urgent: false,
        currency: "RUB",
        production_cost: 0,
        budget: 0,
        sample_cost: 0,
        tirazh_cost: 0,
        prepaid: 0,
        team: [],
        brief_data: {},
        dimensions: "",
      },
      {
        onSuccess: (task) => {
          onClose();
          if (task) navigate(`/pipeline?open=${task.code}`);
        },
        onError: (e) => setError(apiErrorMessage(e, "Не удалось создать задачу")),
      },
    );
  }

  return (
    <Modal title="Новая задача" onClose={onClose}>
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
      <div className={forms.row}>
        <label className={forms.label}>Название</label>
        <input className={forms.input} value={name} onChange={(e) => setName(e.target.value)} />
      </div>
      <div className={forms.grid2}>
        <div className={forms.row}>
          <label className={forms.label}>Дата отгрузки в ТТ</label>
          <input
            type="date"
            className={forms.input}
            value={deadline}
            onChange={(e) => setDeadline(e.target.value)}
          />
        </div>
        <div className={forms.row}>
          <label className={forms.label}>Дата предполагаемого лонча</label>
          <input
            type="date"
            className={forms.input}
            value={launch}
            onChange={(e) => setLaunch(e.target.value)}
          />
        </div>
      </div>
      <p style={{ fontSize: 11, color: "var(--text3)", marginTop: -4, marginBottom: 8 }}>
        Можно оставить пустым и заполнить позже на вкладке «ТЗ» — но без них задача не сможет
        перейти на этап «Дизайн».
      </p>
      <div className={forms.error}>{error}</div>
      <Button variant="primary" disabled={create.isPending || !name.trim()} onClick={submit}>
        Создать
      </Button>
    </Modal>
  );
}
