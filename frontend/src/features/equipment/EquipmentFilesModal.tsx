import { t, tServer } from "../../i18n";
import { useState } from "react";

import { Modal } from "../../components/Modal/Modal";
import { FileInput } from "../../components/FileInput/FileInput";
import { downloadFile } from "../../api/client";
import {
  useDeleteEquipmentDocument,
  useEquipmentDocuments,
  useUploadEquipmentDocument,
} from "../../api/queries/equipment";
import forms from "../../styles/forms.module.css";

const KIND_OPTIONS = [
  { value: "photo", label: t("Фото") },
  { value: "model3d", label: t("Визуализация") },
  { value: "brief", label: t("ТЗ") },
  { value: "ds", label: t("ДС") },
  { value: "invoice", label: t("Счёт") },
  { value: "planogram", label: t("Планограмма") },
  { value: "other", label: t("Прочее") },
];

export function EquipmentFilesModal({
  id,
  name,
  onClose,
}: {
  id: number;
  name: string;
  onClose: () => void;
}) {
  const { data, isLoading } = useEquipmentDocuments(id);
  const upload = useUploadEquipmentDocument(id);
  const del = useDeleteEquipmentDocument(id);
  const [kind, setKind] = useState("photo");

  function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    upload.mutate({ file, kind });
    e.target.value = "";
  }

  return (
    <Modal title={`📁 ${name}`} sub={t("Файлы проекта")} onClose={onClose}>
      <div style={{ display: "flex", flexDirection: "column", gap: 6, marginBottom: 12 }}>
        {isLoading && <span style={{ fontSize: 12, color: "var(--text3)" }}>{t("Загрузка…")}</span>}
        {(data ?? []).map((d) => (
          <div
            key={d.id}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              background: "var(--surface2)",
              border: "1px solid var(--border)",
              borderRadius: 8,
              padding: "7px 12px",
              fontSize: 11,
            }}
          >
            <a
              style={{ color: "var(--accent)", cursor: "pointer", flex: 1 }}
              onClick={() => downloadFile(d.download_url, d.filename)}
            >
              <b>{tServer(d.kind_label)}:</b> {d.filename}
            </a>
            <span style={{ color: "var(--text3)" }}>
              {(d.size / 1024).toFixed(0)} {t("КБ")}
            </span>
            <button
              onClick={() => del.mutate(d.id)}
              style={{
                background: "none",
                border: "none",
                color: "var(--text3)",
                cursor: "pointer",
              }}
            >
              ✕
            </button>
          </div>
        ))}
        {!isLoading && (data ?? []).length === 0 && (
          <span style={{ fontSize: 12, color: "var(--text3)" }}>
            {t("Файлов проекта пока нет")}
          </span>
        )}
      </div>
      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
        <select
          className={forms.select}
          value={kind}
          onChange={(e) => setKind(e.target.value)}
          style={{ width: "auto" }}
        >
          {KIND_OPTIONS.map((k) => (
            <option key={k.value} value={k.value}>
              {k.label}
            </option>
          ))}
        </select>
        <FileInput onChange={handleFile} disabled={upload.isPending} />
        {upload.isPending && (
          <span style={{ fontSize: 11, color: "var(--text3)" }}>{t("Загрузка…")}</span>
        )}
      </div>
    </Modal>
  );
}
