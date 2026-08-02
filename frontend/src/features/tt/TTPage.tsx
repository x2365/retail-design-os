import { useMemo, useState } from "react";

import { Badge } from "../../components/Badge/Badge";
import { Button } from "../../components/Button/Button";
import { Panel } from "../../components/Panel/Panel";
import { useAuth } from "../../auth/AuthContext";
import { downloadFile } from "../../api/client";
import { useDeletePoint, useRetailPoints } from "../../api/queries/retailPoints";
import type { components } from "../../api/schema";
import { TTMini } from "../dashboard/TTMini";
import forms from "../../styles/forms.module.css";
import { PointDetailModal } from "./PointDetailModal";
import { PointFormModal } from "./PointFormModal";
import styles from "./TTPage.module.css";

type PointRow = components["schemas"]["RetailPointOut"];

export default function TTPage() {
  const { isEditor } = useAuth();
  const { data, isLoading } = useRetailPoints();
  const deletePoint = useDeletePoint();
  const [search, setSearch] = useState("");
  const [problemsOnly, setProblemsOnly] = useState(false);
  const [editing, setEditing] = useState<PointRow | "new" | null>(null);
  const [viewing, setViewing] = useState<PointRow | null>(null);

  const points = useMemo(() => {
    let list = data?.items ?? [];
    if (problemsOnly) list = list.filter((p) => p.problems > 0);
    const q = search.trim().toLowerCase();
    if (q) {
      list = list.filter(
        (p) =>
          p.name.toLowerCase().includes(q) ||
          p.city.toLowerCase().includes(q) ||
          p.code.toLowerCase().includes(q),
      );
    }
    return list;
  }, [data, search, problemsOnly]);

  return (
    <div>
      <div style={{ marginBottom: 20 }}>
        <Panel title="СТАТУС ТОРГОВЫХ ТОЧЕК — АКТИВНЫЕ ЛОНЧИ">
          <TTMini />
        </Panel>
      </div>

      {editing && (
        <PointFormModal
          point={editing === "new" ? null : editing}
          onClose={() => setEditing(null)}
        />
      )}
      {viewing && <PointDetailModal point={viewing} onClose={() => setViewing(null)} />}

      <Panel
        title="КАТАЛОГ ТОРГОВЫХ ТОЧЕК"
        count={isLoading ? undefined : points.length}
        actions={
          <>
            <Button
              variant="ghost"
              onClick={() => downloadFile("/api/export/retail-points.csv", "retail-points.csv")}
            >
              ↓ Точки CSV
            </Button>
            <Button
              variant="ghost"
              onClick={() => downloadFile("/api/export/deliveries.csv", "deliveries.csv")}
            >
              ↓ Доставки CSV
            </Button>
            {isEditor && (
              <Button variant="primary" onClick={() => setEditing("new")}>
                + Точка
              </Button>
            )}
          </>
        }
      >
        <div className={styles.toolbar}>
          <input
            className={[forms.input, styles.search].join(" ")}
            style={{ marginBottom: 0 }}
            placeholder="Поиск по названию, городу, коду…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <Button
            variant={problemsOnly ? "primary" : "ghost"}
            onClick={() => setProblemsOnly((v) => !v)}
          >
            ⚠ Только с проблемами
          </Button>
        </div>

        {isLoading ? (
          <p style={{ color: "var(--text3)", fontSize: 12 }}>Загрузка…</p>
        ) : points.length === 0 ? (
          <p style={{ color: "var(--text3)", fontSize: 12 }}>Точек не найдено</p>
        ) : (
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Код</th>
                <th>Название</th>
                <th>Город</th>
                <th>Отгрузки</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {points.map((p) => (
                <tr key={p.id}>
                  <td>
                    <Badge color="gray">{p.code}</Badge>
                  </td>
                  <td>{p.name}</td>
                  <td>{p.city || "—"}</td>
                  <td>
                    {p.deliveries_total ? (
                      `${p.deliveries_total} поз.`
                    ) : (
                      <span style={{ color: "var(--text3)" }}>—</span>
                    )}
                    {p.problems > 0 && (
                      <span style={{ marginLeft: 6 }}>
                        <Badge color="red">⚠ {p.problems}</Badge>
                      </span>
                    )}
                  </td>
                  <td style={{ textAlign: "right", whiteSpace: "nowrap" }}>
                    <button className={styles.iconBtn} onClick={() => setViewing(p)}>
                      Что отгружено
                    </button>
                    {isEditor && (
                      <>
                        <button
                          className={styles.iconBtn}
                          title="Изменить"
                          onClick={() => setEditing(p)}
                        >
                          ✎
                        </button>
                        <button
                          className={styles.iconBtn}
                          title="Удалить"
                          onClick={() => {
                            if (
                              confirm(`Удалить точку «${p.name}»? (только если в неё нет отгрузок)`)
                            ) {
                              deletePoint.mutate(p.id);
                            }
                          }}
                        >
                          ✕
                        </button>
                      </>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Panel>
    </div>
  );
}
