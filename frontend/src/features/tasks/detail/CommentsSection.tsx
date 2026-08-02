import { useState } from "react";

import { Button } from "../../../components/Button/Button";
import forms from "../../../styles/forms.module.css";
import { useAddComment, useTaskComments } from "../../../api/queries/taskDetail";

export function CommentsSection({ code }: { code: string }) {
  const { data, isLoading } = useTaskComments(code);
  const addComment = useAddComment(code);
  const [text, setText] = useState("");

  function submit() {
    const trimmed = text.trim();
    if (!trimmed) return;
    addComment.mutate(trimmed, { onSuccess: () => setText("") });
  }

  return (
    <div>
      <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 10 }}>
        {isLoading && <span style={{ fontSize: 12, color: "var(--text3)" }}>Загрузка…</span>}
        {(data ?? []).map((c) => (
          <div key={c.id} style={{ fontSize: 12 }}>
            <span style={{ fontWeight: 500 }}>{c.author}</span>{" "}
            <span style={{ color: "var(--text3)", fontSize: 10 }}>{c.at}</span>
            <div>{c.text}</div>
          </div>
        ))}
        {!isLoading && (data ?? []).length === 0 && (
          <span style={{ fontSize: 12, color: "var(--text3)" }}>Пока нет комментариев</span>
        )}
      </div>
      <div style={{ display: "flex", gap: 8 }}>
        <textarea
          className={forms.textarea}
          style={{ minHeight: 48, flex: 1 }}
          placeholder="Комментарий…"
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <Button variant="ghost" disabled={addComment.isPending} onClick={submit}>
          Отправить
        </Button>
      </div>
    </div>
  );
}
