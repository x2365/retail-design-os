import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { Badge } from "../../components/Badge/Badge";
import { Button } from "../../components/Button/Button";
import { DocumentPreview } from "../../components/DocumentPreview/DocumentPreview";
import { Panel } from "../../components/Panel/Panel";
import { useAuth } from "../../auth/AuthContext";
import { apiErrorMessage } from "../../api/client";
import {
  useDeleteEquipment,
  useEquipment,
  useProduceEquipment,
  useUpdateEquipment,
} from "../../api/queries/equipment";
import type { components } from "../../api/schema";
import { groupColor } from "../../lib/colors";
import { formatMoneyShort, kopToRub } from "../../lib/money";
import forms from "../../styles/forms.module.css";
import { EquipmentFilesModal } from "./EquipmentFilesModal";
import { EquipmentFormModal } from "./EquipmentFormModal";
import { KIND_LABELS } from "./kindLabels";
import styles from "./EquipmentPage.module.css";

type Equipment = components["schemas"]["EquipmentOut"];

export default function EquipmentPage() {
  const { isEditor } = useAuth();
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const { data, isLoading } = useEquipment(search || undefined);
  const deleteEq = useDeleteEquipment();
  const updateEq = useUpdateEquipment();
  const produce = useProduceEquipment();
  const [editing, setEditing] = useState<Equipment | "new" | null>(null);
  const [files, setFiles] = useState<Equipment | null>(null);
  const [error, setError] = useState("");

  const byBrand = useMemo(() => {
    const map = new Map<string, Equipment[]>();
    for (const e of data ?? []) {
      if (!map.has(e.brand)) map.set(e.brand, []);
      map.get(e.brand)!.push(e);
    }
    return map;
  }, [data]);

  async function handleProduce(e: Equipment) {
    setError("");
    try {
      const task = await produce.mutateAsync(e.id);
      if (task) navigate(`/pipeline?open=${task.code}`);
    } catch (err) {
      setError(apiErrorMessage(err, "Не удалось запустить в производство"));
    }
  }

  return (
    <div>
      {editing && (
        <EquipmentFormModal
          equipment={editing === "new" ? null : editing}
          onClose={() => setEditing(null)}
        />
      )}
      {files && (
        <EquipmentFilesModal id={files.id} name={files.name} onClose={() => setFiles(null)} />
      )}

      <div className={styles.searchRow} style={{ display: "flex", gap: 8, alignItems: "center" }}>
        <input
          className={forms.input}
          style={{ marginBottom: 0, flex: 1 }}
          placeholder="Поиск по названию…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        {isEditor && (
          <Button variant="primary" onClick={() => setEditing("new")}>
            + Изделие
          </Button>
        )}
      </div>
      {error && <div className={forms.error}>{error}</div>}

      {isLoading ? (
        <p style={{ color: "var(--text2)" }}>Загрузка…</p>
      ) : byBrand.size === 0 ? (
        <p style={{ color: "var(--text3)", fontSize: 12 }}>Библиотека пуста</p>
      ) : (
        [...byBrand.entries()].map(([brand, items]) => (
          <div className={styles.groupWrap} key={brand}>
            <Panel
              title={brand}
              count={items.length}
              leading={
                <div
                  style={{
                    width: 10,
                    height: 10,
                    borderRadius: 3,
                    background: groupColor(items[0].group),
                  }}
                />
              }
            >
              <div className={styles.cards}>
                {items.map((e) => (
                  <div
                    className={[styles.card, e.is_active ? "" : styles.archived].join(" ")}
                    key={e.id}
                  >
                    {e.cover_document_id != null && (
                      <DocumentPreview
                        downloadUrl={`/api/documents/${e.cover_document_id}/download`}
                        filename={e.name}
                        size="cover"
                      />
                    )}
                    <div className={styles.cardBody}>
                      <div className={styles.topRow}>
                        <Badge color="blue">{KIND_LABELS[e.kind] ?? e.kind}</Badge>
                        {!e.is_active && <Badge color="gray">архив</Badge>}
                        <span className={styles.produced}>в производстве {e.times_produced}×</span>
                      </div>
                      <div className={styles.name}>{e.name}</div>
                      <div className={styles.meta}>
                        {e.dimensions || "—"}
                        {e.description ? ` · ${e.description}` : ""}
                      </div>
                      <div className={styles.budget}>
                        Бюджет:{" "}
                        <b style={{ color: "var(--text)" }}>
                          {formatMoneyShort(kopToRub(e.est_budget))} ₽
                        </b>
                      </div>
                      <div className={styles.actions}>
                        <Button variant="ghost" onClick={() => setFiles(e)}>
                          📁 Файлы
                        </Button>
                        {isEditor && e.is_active && (
                          <Button
                            variant="primary"
                            disabled={produce.isPending}
                            onClick={() => handleProduce(e)}
                          >
                            В производство →
                          </Button>
                        )}
                        {isEditor && (
                          <>
                            <Button variant="ghost" onClick={() => setEditing(e)}>
                              ✎
                            </Button>
                            <Button
                              variant="ghost"
                              onClick={() =>
                                updateEq.mutate({ id: e.id, payload: { is_active: !e.is_active } })
                              }
                            >
                              {e.is_active ? "В архив" : "Из архива"}
                            </Button>
                            <Button
                              variant="danger"
                              onClick={() => {
                                setError("");
                                if (confirm(`Удалить «${e.name}» из библиотеки?`)) {
                                  deleteEq.mutate(e.id, {
                                    onError: (err) =>
                                      setError(apiErrorMessage(err, "Не удалось удалить изделие")),
                                  });
                                }
                              }}
                            >
                              ✕
                            </Button>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </Panel>
          </div>
        ))
      )}
    </div>
  );
}
