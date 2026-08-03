import { useEffect, useRef, useState } from "react";

import { downloadFile } from "../../api/client";
import {
  useDeleteDocument,
  useTaskDocuments,
  useUploadDocument,
} from "../../api/queries/taskDetail";
import styles from "./DocumentList.module.css";

interface DocumentListProps {
  code: string;
  stage: number;
  kinds: { value: string; label: string }[];
  canEdit: boolean;
}

/** Document upload/list widget shared by every stage tab that has file
 * slots (design sketches, ДС/Счёт, sample photos, shipment docs, …). Each
 * stage passes its own allowed `kinds`; the API's `stage` filter keeps the
 * list scoped without needing a client-side kind filter too. */
export function DocumentList({ code, stage, kinds, canEdit }: DocumentListProps) {
  const { data, isLoading } = useTaskDocuments(code, stage);
  const upload = useUploadDocument(code);
  const del = useDeleteDocument(code);
  const [kind, setKind] = useState(kinds[0]?.value ?? "other");
  const fileRef = useRef<HTMLInputElement>(null);

  // If multiple document kinds are required at this stage (e.g. "ДС и Счёт"
  // needs both), keep the selector pointed at whichever kind is still
  // missing — otherwise it's easy to upload both files under the same kind
  // without noticing, and the stage silently never becomes eligible to
  // advance (its precondition checks each kind separately).
  useEffect(() => {
    if (kinds.length <= 1) return;
    const present = new Set((data ?? []).map((d) => d.kind));
    setKind((current) => {
      if (!present.has(current)) return current;
      const nextMissing = kinds.find((k) => !present.has(k.value));
      return nextMissing ? nextMissing.value : current;
    });
  }, [data, kinds]);

  function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    upload.mutate({ file, kind, stage });
    e.target.value = "";
  }

  return (
    <div>
      {kinds.length > 1 && (
        <div className={styles.checklist}>
          {kinds.map((k) => {
            const has = (data ?? []).some((d) => d.kind === k.value);
            return (
              <span key={k.value} className={has ? styles.checkDone : styles.checkMissing}>
                {has ? "✓" : "○"} {k.label}
              </span>
            );
          })}
        </div>
      )}
      <div className={styles.list}>
        {isLoading && <span style={{ fontSize: 12, color: "var(--text3)" }}>Загрузка…</span>}
        {(data ?? []).map((d) => (
          <div className={styles.item} key={d.id}>
            <a className={styles.link} onClick={() => downloadFile(d.download_url, d.filename)}>
              📎 {d.filename}
            </a>
            <span style={{ color: "var(--text3)", fontSize: 10 }}>{d.kind_label}</span>
            {canEdit && (
              <button className={styles.del} onClick={() => del.mutate(d.id)} title="Удалить">
                ✕
              </button>
            )}
          </div>
        ))}
        {!isLoading && (data ?? []).length === 0 && (
          <span style={{ fontSize: 12, color: "var(--text3)" }}>Нет файлов</span>
        )}
      </div>
      {canEdit && (
        <div className={styles.uploadRow}>
          {kinds.length > 1 && (
            <select value={kind} onChange={(e) => setKind(e.target.value)} style={{ fontSize: 11 }}>
              {kinds.map((k) => (
                <option key={k.value} value={k.value}>
                  {k.label}
                </option>
              ))}
            </select>
          )}
          <input ref={fileRef} type="file" onChange={handleFile} style={{ fontSize: 11 }} />
          {upload.isPending && (
            <span style={{ fontSize: 11, color: "var(--text3)" }}>Загрузка…</span>
          )}
        </div>
      )}
    </div>
  );
}
