import { useState } from "react";

import { Button } from "../../components/Button/Button";
import { Panel } from "../../components/Panel/Panel";
import { useAuth } from "../../auth/AuthContext";
import { useBrands, useDeleteBrand } from "../../api/queries/brands";
import { useGroups } from "../../api/queries/groups";
import type { components } from "../../api/schema";
import { BrandFormModal } from "./BrandFormModal";
import styles from "./BrandsPage.module.css";

type Brand = components["schemas"]["BrandOut"];

export default function BrandsPage() {
  const { isEditor } = useAuth();
  const { data: groups, isLoading: groupsLoading } = useGroups();
  const { data: brands, isLoading: brandsLoading } = useBrands();
  const deleteBrand = useDeleteBrand();
  const [editing, setEditing] = useState<{ brand: Brand | null; groupCode: string } | null>(null);

  if (groupsLoading || brandsLoading) return <p style={{ color: "var(--text2)" }}>Загрузка…</p>;

  return (
    <div className={styles.grid}>
      {editing && (
        <BrandFormModal
          brand={editing.brand}
          groupCode={editing.groupCode}
          onClose={() => setEditing(null)}
        />
      )}
      {(groups ?? []).map((g) => {
        const groupBrands = (brands ?? []).filter((b) => b.group === g.code);
        return (
          <Panel
            key={g.code}
            title={g.name}
            leading={<div className={styles.dot} style={{ background: g.color }} />}
            count={groupBrands.length}
            actions={
              isEditor ? (
                <Button
                  variant="ghost"
                  onClick={() => setEditing({ brand: null, groupCode: g.code })}
                >
                  + Бренд
                </Button>
              ) : undefined
            }
          >
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {groupBrands.map((b) => (
                <div className={styles.row} key={b.id}>
                  <div
                    className={styles.avatar}
                    style={{ background: `${g.color}22`, color: g.color }}
                  >
                    {b.name[0]}
                  </div>
                  <div style={{ flex: 1 }}>
                    <div className={styles.name}>{b.name}</div>
                    <div className={styles.meta}>
                      {b.active_tasks} активных · {b.equipment_count} в библиотеке
                    </div>
                  </div>
                  {isEditor && (
                    <>
                      <button
                        className={styles.iconBtn}
                        title="Изменить"
                        onClick={() => setEditing({ brand: b, groupCode: g.code })}
                      >
                        ✎
                      </button>
                      <button
                        className={styles.iconBtn}
                        title="Удалить"
                        onClick={() => {
                          if (confirm(`Удалить бренд «${b.name}»?`)) deleteBrand.mutate(b.id);
                        }}
                      >
                        ✕
                      </button>
                    </>
                  )}
                </div>
              ))}
              {groupBrands.length === 0 && (
                <p style={{ color: "var(--text3)", fontSize: 11 }}>Нет брендов в группе</p>
              )}
            </div>
          </Panel>
        );
      })}
    </div>
  );
}
