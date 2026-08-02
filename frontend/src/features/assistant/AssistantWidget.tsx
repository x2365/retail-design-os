import { useState } from "react";
import { useLocation } from "react-router-dom";

import { Badge } from "../../components/Badge/Badge";
import { Button } from "../../components/Button/Button";
import { useAskAssistant, useAssistantStatus } from "../../api/queries/assistant";
import { ROUTE_TITLES } from "../../app/navConfig";
import styles from "./AssistantWidget.module.css";

interface Turn {
  query: string;
  answer: string;
  usedTools: string[];
}

/** Floating copilot widget — talks to the backend's local, read-only,
 * tool-calling LLM assistant (see backend/app/services/assistant.py).
 * Nothing here calls a model directly; it's a thin chat UI over
 * GET /assistant/status + POST /assistant. */
export function AssistantWidget() {
  const { data: status } = useAssistantStatus();
  const ask = useAskAssistant();
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);

  if (!status) return null;

  function submit() {
    const q = query.trim();
    if (!q) return;
    setQuery("");
    const screen = ROUTE_TITLES[location.pathname] ?? location.pathname;
    ask.mutate(
      { query: q, screen },
      {
        onSuccess: (res) => {
          setTurns((t) => [
            ...t,
            { query: q, answer: res.answer, usedTools: res.used_tools ?? [] },
          ]);
        },
      },
    );
  }

  if (!open) {
    return (
      <button className={styles.fab} onClick={() => setOpen(true)} title="Ассистент">
        💬
      </button>
    );
  }

  return (
    <div className={styles.panel}>
      <div className={styles.header}>
        <div className={styles.title}>Ассистент-копайлот</div>
        <button className={styles.close} onClick={() => setOpen(false)}>
          ✕
        </button>
      </div>

      {!status.enabled ? (
        <div className={styles.disabled}>
          Ассистент выключен. Запустите Ollama с моделью «{status.model}» и включите LLM_ENABLED,
          чтобы пользоваться копайлотом.
        </div>
      ) : (
        <>
          <div className={styles.log}>
            {turns.length === 0 && (
              <div style={{ fontSize: 12, color: "var(--text3)" }}>
                Спросите про задачи, бюджеты, согласования или доставки — ассистент отвечает только
                на основе реальных данных дашборда.
              </div>
            )}
            {turns.map((t, i) => (
              <div key={i}>
                <div className={styles.turnQuery}>{t.query}</div>
                <div className={styles.turnAnswer}>
                  {t.answer}
                  {t.usedTools.length > 0 && (
                    <div className={styles.tools}>
                      {t.usedTools.map((tool, j) => (
                        <Badge color="blue" key={j}>
                          {tool}
                        </Badge>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
            {ask.isPending && <div style={{ fontSize: 12, color: "var(--text3)" }}>Думаю…</div>}
          </div>
          <div className={styles.inputRow}>
            <input
              className={styles.input}
              placeholder="Спросить про задачи…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && submit()}
            />
            <Button variant="primary" disabled={ask.isPending || !query.trim()} onClick={submit}>
              →
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
