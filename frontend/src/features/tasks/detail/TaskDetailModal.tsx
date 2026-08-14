import { useEffect, useRef, useState } from "react";

import { ApprovalGate } from "../../../components/ApprovalGate/ApprovalGate";
import { Badge } from "../../../components/Badge/Badge";
import { Button } from "../../../components/Button/Button";
import { DocumentList } from "../../../components/DocumentList/DocumentList";
import { DocumentPreview } from "../../../components/DocumentPreview/DocumentPreview";
import { Modal } from "../../../components/Modal/Modal";
import { NumberInput } from "../../../components/NumberInput/NumberInput";
import { useAuth } from "../../../auth/AuthContext";
import { canApproveGate } from "../../../auth/roles";
import { apiErrorMessage } from "../../../api/client";
import { useGroups } from "../../../api/queries/groups";
import {
  useAddComment,
  useContractors,
  useCreateContractor,
  useDeleteTask,
  useKpApproval,
  usePrepApproval,
  useSampleApproval,
  useSetStageApproval,
  useTask,
  useTaskDocuments,
  useUpdateTask,
} from "../../../api/queries/taskDetail";
import { ruDateToIso } from "../../../lib/dates";
import { formatMoney, kopToRub } from "../../../lib/money";
import {
  FINAL_APPROVAL_STAGE,
  INSTALL_STAGE,
  LAST_STAGE,
  STAGE_TAB_LABELS,
  TOTAL_STAGES,
  nextStageFor,
  prevStageFor,
  showsInstallStage,
} from "../../../lib/stages";
import forms from "../../../styles/forms.module.css";
import { CommentsSection } from "./CommentsSection";
import { DeliveriesList } from "./DeliveriesList";
import { InstallationList } from "./InstallationList";
import styles from "./TaskDetailModal.module.css";

// Соответствует PS_LABELS в backend/app/serializers.py::payment_to_out
const PAYMENT_STATUS_LABELS: Record<string, string> = {
  unpaid: "Ожидает оплаты",
  registry: "Отправлен в реестр",
  queued: "Заведён на оплату",
  prepaid: "Предоплачен",
  paid: "Оплачено",
};

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <div className={styles.fieldLabel}>{label}</div>
      <div className={styles.fieldValue}>{value || "—"}</div>
    </div>
  );
}

export function TaskDetailModal({ code, onClose }: { code: string; onClose: () => void }) {
  const { data: task, isLoading } = useTask(code);
  const { isEditor, user } = useAuth();
  const [viewedStage, setViewedStage] = useState<number | null>(null);
  const [error, setError] = useState("");
  const updateTask = useUpdateTask(code);
  const prepApproval = usePrepApproval(code);
  const kpApproval = useKpApproval(code);
  const sampleApproval = useSampleApproval(code);
  const setStageApproval = useSetStageApproval(code);
  const deleteTask = useDeleteTask(code);
  const prevTaskStageRef = useRef<number | null>(null);

  useEffect(() => {
    if (!task) return;
    if (viewedStage === null) {
      setViewedStage(task.stage);
    } else if (
      prevTaskStageRef.current !== null &&
      prevTaskStageRef.current !== task.stage &&
      viewedStage === prevTaskStageRef.current
    ) {
      // The stage being viewed just auto-advanced server-side out from under
      // it (e.g. approving both КП gates jumps 5->6 with no button click) —
      // follow it. Otherwise "Далее" silently targets task.stage+1, skipping
      // the tab the user never saw, and fails that tab's own precondition
      // check instead ("Документы не завершён" while looking at "КП").
      setViewedStage(task.stage);
    }
    prevTaskStageRef.current = task.stage;
  }, [task, viewedStage]);

  if (isLoading || !task || viewedStage === null) {
    return (
      <Modal title="Загрузка…" onClose={onClose}>
        <p style={{ color: "var(--text2)" }}>Загрузка карточки задачи…</p>
      </Modal>
    );
  }

  async function advance() {
    setError("");
    const next = nextStageFor(task!.stage, task!.equipment_kind);
    try {
      await updateTask.mutateAsync({ stage: next });
      setViewedStage(next);
    } catch (e) {
      setError(apiErrorMessage(e, "Не удалось перейти на следующий этап"));
    }
  }

  async function revert() {
    setError("");
    const prev = prevStageFor(task!.stage, task!.equipment_kind);
    try {
      await updateTask.mutateAsync({ stage: prev });
      setViewedStage(prev);
    } catch (e) {
      setError(apiErrorMessage(e, "Не удалось вернуться на предыдущий этап"));
    }
  }

  async function handleDelete() {
    if (
      !confirm(
        `Удалить задачу ${task!.code} безвозвратно? Это удалит всю историю, документы, оплату и комментарии.`,
      )
    ) {
      return;
    }
    setError("");
    try {
      await deleteTask.mutateAsync();
      onClose();
    } catch (e) {
      setError(apiErrorMessage(e, "Не удалось удалить задачу"));
    }
  }

  return (
    <Modal
      title={`${task.code} · ${task.name}`}
      sub={
        <>
          {task.brand} · Группа {task.group} · {task.urgent && <Badge color="red">Срочно</Badge>}
        </>
      }
      headerExtra={
        user?.role === "admin" ? (
          <Button variant="ghost" disabled={deleteTask.isPending} onClick={handleDelete}>
            🗑 Удалить
          </Button>
        ) : undefined
      }
      onClose={onClose}
    >
      <div className={styles.stagesWrap}>
        <div className={styles.stages}>
          {Array.from({ length: TOTAL_STAGES }, (_, i) => i + 1).map((s) => {
            const label = STAGE_TAB_LABELS[s];
            if (!showsInstallStage(task.equipment_kind) && s === INSTALL_STAGE) return null;
            const cls =
              s === viewedStage
                ? styles.stageActive
                : s < task.stage
                  ? styles.stageDone
                  : styles.stage;
            return (
              <button
                key={s}
                className={[styles.stage, cls].join(" ")}
                onClick={() => setViewedStage(s)}
              >
                {s}. {label}
              </button>
            );
          })}
        </div>
      </div>

      <StageContent
        stage={viewedStage}
        task={task}
        code={code}
        isEditor={isEditor}
        canMoney={user?.role === "admin"}
        canApprove={(gate) => canApproveGate(user?.role, gate)}
        prepApproval={prepApproval}
        kpApproval={kpApproval}
        sampleApproval={sampleApproval}
        setStageApproval={setStageApproval}
        updateTask={updateTask}
        setError={setError}
      />

      <div className={styles.sectionLabel}>Комментарии и обсуждение</div>
      <CommentsSection code={code} />

      <div className={styles.footer}>
        {isEditor && task.stage > 1 && (
          <Button variant="ghost" disabled={updateTask.isPending} onClick={revert}>
            ← На предыдущий этап
          </Button>
        )}
        {isEditor && task.stage < LAST_STAGE && (
          <Button variant="primary" disabled={updateTask.isPending} onClick={advance}>
            Далее →
          </Button>
        )}
        {error && <span className={styles.error}>{error}</span>}
      </div>
    </Modal>
  );
}

// ---- per-stage content -----------------------------------------------------

type TaskOutT = NonNullable<ReturnType<typeof useTask>["data"]>;

interface StageContentProps {
  stage: number;
  task: TaskOutT;
  code: string;
  isEditor: boolean;
  canMoney: boolean;
  canApprove: (gate: string) => boolean;
  prepApproval: ReturnType<typeof usePrepApproval>;
  kpApproval: ReturnType<typeof useKpApproval>;
  sampleApproval: ReturnType<typeof useSampleApproval>;
  setStageApproval: ReturnType<typeof useSetStageApproval>;
  updateTask: ReturnType<typeof useUpdateTask>;
  setError: (msg: string) => void;
}

function StageContent(props: StageContentProps) {
  const { stage, task, code, isEditor } = props;

  if (stage === 1) return <BriefStage {...props} />;
  if (stage === 2)
    return (
      <div>
        <div className={styles.sectionLabel}>Файлы дизайна (эскиз / 3D / фото)</div>
        <DocumentList
          code={code}
          stage={2}
          canEdit={isEditor}
          kinds={[
            { value: "sketch", label: "Эскиз" },
            { value: "model3d", label: "3D-модель" },
            { value: "photo", label: "Фото" },
          ]}
        />
      </div>
    );
  if (stage === 3)
    return (
      <div>
        <PrepStage {...props} />
        <details style={{ marginTop: 16 }}>
          <summary className={styles.sectionLabel} style={{ cursor: "pointer" }}>
            Summary
          </summary>
          <div style={{ marginTop: 8 }}>
            <SummaryStage {...props} />
          </div>
        </details>
      </div>
    );
  if (stage === 4) return <KpStage {...props} />;
  if (stage === 5)
    return (
      <div>
        <div className={styles.sectionLabel}>Документы</div>
        <DocumentList
          code={code}
          stage={5}
          canEdit={isEditor}
          kinds={[
            { value: "ds", label: "ДС" },
            { value: "invoice", label: "Счёт" },
          ]}
        />
      </div>
    );
  if (stage === 6) return <SampleStage {...props} />;
  if (stage === 7)
    return (
      <div>
        <ShipmentStage {...props} />
        <div style={{ marginTop: 16 }}>
          <div className={styles.sectionLabel}>Доставка в ТТ</div>
          <DeliveriesList code={code} />
        </div>
      </div>
    );
  if (stage === INSTALL_STAGE) {
    if (!showsInstallStage(task.equipment_kind)) {
      return (
        <p style={{ fontSize: 12, color: "var(--text3)" }}>
          Монтаж не требуется для этого типа изделия.
        </p>
      );
    }
    return (
      <div>
        <div className={styles.sectionLabel}>Монтаж в ТТ</div>
        <InstallationList code={code} />
      </div>
    );
  }
  if (stage === FINAL_APPROVAL_STAGE) return <FinalStage {...props} />;
  if (stage === LAST_STAGE) {
    return (
      <div>
        <Badge color="green">✓ Задача закрыта</Badge>
        <div className={styles.grid2} style={{ marginTop: 16 }}>
          <Field label="Бюджет" value={formatMoney(kopToRub(task.kp_total))} />
          <Field label="Статус оплаты" value={task.payment_status} />
        </div>
      </div>
    );
  }
  return null;
}

function BriefStage({ task, code, isEditor, updateTask, setError }: StageContentProps) {
  const [article, setArticle] = useState(task.article);
  const [dimensions, setDimensions] = useState(task.dimensions);
  const [packagingPrimary, setPackagingPrimary] = useState(task.packaging_primary);
  const [deadline, setDeadline] = useState(ruDateToIso(task.deadline));
  const [launch, setLaunch] = useState(ruDateToIso(task.launch));

  async function save() {
    setError("");
    if (dimensions.trim() && !/^\d+(\.\d+)?\s\d+(\.\d+)?\s\d+(\.\d+)?$/.test(dimensions.trim())) {
      setError("Размеры — 3 числа через пробел (Ш В Г), например: 300 300 20");
      return;
    }
    try {
      await updateTask.mutateAsync({
        article,
        dimensions,
        packaging_primary: packagingPrimary,
        deadline: deadline || undefined,
        launch: launch || undefined,
      });
    } catch (e) {
      setError(apiErrorMessage(e, "Не удалось сохранить ТЗ"));
    }
  }

  if (!isEditor) {
    return (
      <div className={styles.grid2}>
        <Field label="Артикул" value={task.article} />
        <Field label="Размеры, мм (Ш В Г)" value={task.dimensions} />
        <Field label="Первичная упаковка" value={task.packaging_primary} />
        <Field label="Дата отгрузки в ТТ" value={task.deadline} />
        <Field label="Дата предполагаемого лонча" value={task.launch} />
      </div>
    );
  }

  return (
    <div>
      <div className={forms.grid2}>
        <div className={forms.row}>
          <label className={forms.label}>Артикул</label>
          <input
            className={forms.input}
            value={article}
            onChange={(e) => setArticle(e.target.value)}
          />
        </div>
        <div className={forms.row}>
          <label className={forms.label}>Размеры, мм (Ш В Г)</label>
          <input
            className={forms.input}
            value={dimensions}
            onChange={(e) => setDimensions(e.target.value)}
            placeholder="300 300 20"
          />
        </div>
      </div>
      <div className={forms.row}>
        <label className={forms.label}>Первичная упаковка</label>
        <input
          className={forms.input}
          value={packagingPrimary}
          onChange={(e) => setPackagingPrimary(e.target.value)}
        />
      </div>
      <div className={forms.grid2}>
        <div className={forms.row}>
          <label className={forms.label}>Дата отгрузки в ТТ *</label>
          <input
            type="date"
            className={forms.input}
            value={deadline}
            onChange={(e) => setDeadline(e.target.value)}
          />
        </div>
        <div className={forms.row}>
          <label className={forms.label}>Дата предполагаемого лонча *</label>
          <input
            type="date"
            className={forms.input}
            value={launch}
            onChange={(e) => setLaunch(e.target.value)}
          />
        </div>
      </div>
      <p style={{ fontSize: 11, color: "var(--text3)", marginTop: -4, marginBottom: 8 }}>
        * обязательно для перехода на «Дизайн»
      </p>
      <Button variant="ghost" disabled={updateTask.isPending} onClick={save}>
        Сохранить
      </Button>
      <div style={{ marginTop: 16 }}>
        <div className={styles.sectionLabel}>Файл ТЗ (если есть)</div>
        <DocumentList
          code={code}
          stage={1}
          canEdit={isEditor}
          kinds={[{ value: "brief", label: "ТЗ" }]}
        />
      </div>
    </div>
  );
}

function PrepStage({
  task,
  code,
  isEditor,
  canApprove,
  prepApproval,
  setError,
}: StageContentProps) {
  const both = task.prep_brand_approved && task.prep_zya_approved;
  const { data: designDocs } = useTaskDocuments(code, 2);
  const sketch = (designDocs ?? []).find((d) => d.content_type.startsWith("image/"));

  function setGate(gate: "brand" | "zya") {
    return (approved: boolean) => {
      setError("");
      prepApproval.mutate(
        { gate, approved },
        { onError: (e) => setError(apiErrorMessage(e, "Не удалось обновить согласование")) },
      );
    };
  }

  return (
    <div>
      {sketch && (
        <div style={{ marginBottom: 12 }}>
          <div className={styles.sectionLabel}>Эскиз</div>
          <DocumentPreview downloadUrl={sketch.download_url} filename={sketch.filename} />
        </div>
      )}
      <div className={styles.sectionLabel}>Согласование (оба → Бюджет и КП)</div>
      <ApprovalGate
        label="Бренд"
        approved={task.prep_brand_approved}
        by={task.prep_brand_by}
        canEdit={isEditor || canApprove("brand")}
        pending={prepApproval.isPending}
        onSetApproved={setGate("brand")}
      />
      <ApprovalGate
        label="Сеть"
        approved={task.prep_zya_approved}
        by={task.prep_zya_by}
        canEdit={isEditor || canApprove("zya")}
        pending={prepApproval.isPending}
        onSetApproved={setGate("zya")}
      />
      <div style={{ marginTop: 8 }}>
        {both ? (
          <Badge color="green">✓ Оба согласования получены</Badge>
        ) : (
          <span style={{ fontSize: 11, color: "var(--text3)" }}>ожидаются оба согласования</span>
        )}
      </div>
    </div>
  );
}

function SummaryStage({ task }: StageContentProps) {
  return (
    <div className={styles.grid2}>
      <Field label="Бренд" value={task.brand} />
      <Field label="Дедлайн ТТ" value={task.deadline} />
      <Field label="Дата лонча" value={task.launch} />
      <Field label="Артикул" value={task.article} />
      <Field label="Размеры, мм (Ш В Г)" value={task.dimensions} />
      <Field label="Согласование бренда" value={task.prep_brand_approved ? "✓ Согласовано" : "—"} />
      <Field label="Согласование сети" value={task.prep_zya_approved ? "✓ Согласовано" : "—"} />
    </div>
  );
}

function KpStage({
  task,
  code,
  isEditor,
  canMoney,
  canApprove,
  kpApproval,
  updateTask,
  setError,
}: StageContentProps) {
  const { data: contractors } = useContractors();
  const createContractor = useCreateContractor();
  const { data: groups } = useGroups();
  const { data: kpDocs } = useTaskDocuments(code, 4);
  const hasKp = (kpDocs ?? []).some((d) => d.kind === "kp");
  const [addingContractor, setAddingContractor] = useState(false);
  const [newContractorName, setNewContractorName] = useState("");
  const [sampleCost, setSampleCost] = useState(kopToRub(task.sample_cost));
  const [tirazhCost, setTirazhCost] = useState(kopToRub(task.tirazh_cost));
  const [tirazhQty, setTirazhQty] = useState(task.tirazh_qty);

  // Бюджет задачи больше не вводится — это Образец+Тираж, фиксируется
  // бэкендом при согласовании КП (см. kp_approval). Здесь только
  // предупреждаем, если то, что сейчас набрано в полях (ещё не сохранено),
  // превышает остаток бюджета группы — план минус уже освоенное другими
  // задачами. budget_spent уже суммирует бюджет ЭТОЙ задачи тоже, поэтому
  // прибавляем его обратно, иначе остаток занижен на её же сумму.
  const group = groups?.find((g) => g.code === task.group);
  const groupRemaining = group
    ? kopToRub(group.budget_planned - group.budget_spent + task.budget)
    : null;
  const requested = sampleCost + tirazhCost;
  const overBudget = groupRemaining !== null && requested > groupRemaining;

  function setGate(gate: "manager" | "director") {
    return (approved: boolean) => {
      setError("");
      kpApproval.mutate(
        { gate, approved },
        { onError: (e) => setError(apiErrorMessage(e, "Не удалось обновить согласование")) },
      );
    };
  }

  async function saveContractor(name: string) {
    try {
      await updateTask.mutateAsync({ kp_contractor: name });
    } catch (e) {
      setError(apiErrorMessage(e, "Не удалось сохранить подрядчика"));
    }
  }

  async function saveFinance() {
    setError("");
    try {
      await updateTask.mutateAsync({
        sample_cost: Math.round(sampleCost * 100),
        tirazh_cost: Math.round(tirazhCost * 100),
      });
    } catch (e) {
      setError(apiErrorMessage(e, "Не удалось сохранить финансы"));
    }
  }

  // Отдельно от saveFinance: количество (штуки) — не деньги, не должно
  // требовать canMoney и не должно попадать в money_in_payload на бэкенде
  // (иначе PATCH получит 403 для редактора без прав на бюджет).
  async function saveTirazhQty() {
    setError("");
    try {
      await updateTask.mutateAsync({ tirazh_qty: Math.round(tirazhQty) });
    } catch (e) {
      setError(apiErrorMessage(e, "Не удалось сохранить тираж"));
    }
  }

  return (
    <div>
      <div className={forms.row}>
        <label className={forms.label}>Подрядчик</label>
        {isEditor ? (
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <select
              className={forms.select}
              value={task.kp_contractor}
              onChange={(e) => saveContractor(e.target.value)}
            >
              <option value="">—</option>
              {(contractors ?? []).map((c) => (
                <option key={c.id} value={c.name}>
                  {c.name}
                </option>
              ))}
            </select>
            <Button variant="ghost" onClick={() => setAddingContractor((o) => !o)}>
              + Новый
            </Button>
          </div>
        ) : (
          <div className={styles.fieldValue}>{task.kp_contractor || "—"}</div>
        )}
      </div>
      {addingContractor && (
        <div className={forms.row} style={{ display: "flex", gap: 8, alignItems: "flex-end" }}>
          <div style={{ flex: 1 }}>
            <label className={forms.label}>Название подрядчика</label>
            <input
              className={forms.input}
              value={newContractorName}
              onChange={(e) => setNewContractorName(e.target.value)}
            />
          </div>
          <Button
            variant="ghost"
            disabled={createContractor.isPending || !newContractorName.trim()}
            onClick={() => {
              setError("");
              createContractor.mutate(
                { name: newContractorName, contact: "", details: {} },
                {
                  onSuccess: (c) => {
                    setNewContractorName("");
                    setAddingContractor(false);
                    if (c) saveContractor(c.name);
                  },
                  onError: (e) => setError(apiErrorMessage(e, "Не удалось добавить подрядчика")),
                },
              );
            }}
          >
            Добавить
          </Button>
        </div>
      )}

      <Field label="Бюджет" value={formatMoney(kopToRub(task.budget))} />
      {task.budget === 0 && (
        <p style={{ fontSize: 11, color: "var(--text3)", marginTop: -4, marginBottom: 8 }}>
          Считается автоматически как Образец + Тираж — фиксируется, когда КП согласовано
          (Финансы + Бренд ниже).
        </p>
      )}

      <div style={{ marginTop: 12 }}>
        <div className={styles.sectionLabel}>Файл КП</div>
        <DocumentList
          code={code}
          stage={4}
          canEdit={isEditor}
          kinds={[{ value: "kp", label: "КП" }]}
        />
      </div>

      {hasKp ? (
        <div style={{ marginTop: 12 }}>
          <div style={{ marginBottom: 12 }}>
            <Badge color="blue">
              ✓ Заведено на оплату · {PAYMENT_STATUS_LABELS[task.payment_status] ?? task.payment_status}
            </Badge>
          </div>
          {canMoney ? (
            <div className={forms.grid2}>
              <div className={forms.row}>
                <label className={forms.label}>Образец, ₽</label>
                <NumberInput className={forms.input} value={sampleCost} onChange={setSampleCost} />
              </div>
              <div className={forms.row}>
                <label className={forms.label}>Тираж, ₽</label>
                <NumberInput className={forms.input} value={tirazhCost} onChange={setTirazhCost} />
              </div>
            </div>
          ) : (
            <div className={styles.grid2}>
              <Field label="Образец" value={formatMoney(kopToRub(task.sample_cost))} />
              <Field label="Тираж" value={formatMoney(kopToRub(task.tirazh_cost))} />
            </div>
          )}
          {canMoney && overBudget && (
            <p style={{ fontSize: 11, color: "var(--warn)", marginTop: 4 }}>
              ⚠ Образец + Тираж ({formatMoney(requested)}) больше остатка бюджета группы (
              {formatMoney(groupRemaining ?? 0)})
            </p>
          )}

          {isEditor ? (
            <div className={forms.row} style={{ marginTop: 8 }}>
              <label className={forms.label}>Тираж, шт.</label>
              <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <NumberInput className={forms.input} value={tirazhQty} onChange={setTirazhQty} />
                <Button variant="ghost" disabled={updateTask.isPending} onClick={saveTirazhQty}>
                  Сохранить
                </Button>
              </div>
            </div>
          ) : (
            <Field label="Тираж, шт." value={String(task.tirazh_qty)} />
          )}
        </div>
      ) : (
        <p style={{ fontSize: 12, color: "var(--text3)", marginTop: 12 }}>
          Загрузите файл КП, чтобы указать стоимость образца и тиража.
        </p>
      )}

      {canMoney && (
        <Button
          variant="ghost"
          disabled={updateTask.isPending}
          onClick={saveFinance}
          style={{ marginTop: 8 }}
        >
          Сохранить финансы
        </Button>
      )}

      <div className={styles.sectionLabel} style={{ marginTop: 16 }}>
        Согласование КП (оба → Документы)
      </div>
      <ApprovalGate
        label="Финансы"
        approved={task.kp_manager_approved}
        by={task.kp_manager_by}
        canEdit={isEditor || canApprove("manager")}
        pending={kpApproval.isPending}
        onSetApproved={setGate("manager")}
      />
      <ApprovalGate
        label="Бренд"
        approved={task.kp_director_approved}
        by={task.kp_director_by}
        canEdit={isEditor || canApprove("director")}
        pending={kpApproval.isPending}
        onSetApproved={setGate("director")}
      />
    </div>
  );
}

function SampleStage({
  task,
  code,
  isEditor,
  canApprove,
  sampleApproval,
  updateTask,
  setError,
}: StageContentProps) {
  const [status, setStatus] = useState(task.sample_status);

  function setGate(gate: "qc" | "brand" | "network") {
    return (approved: boolean) => {
      setError("");
      sampleApproval.mutate(
        { gate, approved },
        { onError: (e) => setError(apiErrorMessage(e, "Не удалось обновить согласование")) },
      );
    };
  }

  async function saveStatus(next: string) {
    setStatus(next);
    try {
      await updateTask.mutateAsync({ sample_status: next });
    } catch (e) {
      setError(apiErrorMessage(e, "Не удалось сохранить статус образца"));
    }
  }

  return (
    <div>
      <div className={forms.row}>
        <label className={forms.label}>Статус образца</label>
        {isEditor ? (
          <select
            className={forms.select}
            value={status}
            onChange={(e) => saveStatus(e.target.value)}
          >
            <option value="unpaid">Не оплачен</option>
            <option value="paid">Оплачен</option>
            <option value="in_tirazh">В тираже</option>
          </select>
        ) : (
          <div className={styles.fieldValue}>{status}</div>
        )}
      </div>

      <div className={styles.sectionLabel}>Согласование образца</div>
      <ApprovalGate
        label="RD"
        approved={task.sample_qc_approved}
        by={task.sample_qc_by}
        canEdit={isEditor || canApprove("qc")}
        pending={sampleApproval.isPending}
        onSetApproved={setGate("qc")}
      />
      <ApprovalGate
        label="Бренд"
        approved={task.sample_brand_approved}
        by={task.sample_brand_by}
        canEdit={isEditor || canApprove("brand")}
        pending={sampleApproval.isPending}
        onSetApproved={setGate("brand")}
      />
      <ApprovalGate
        label="Сеть"
        approved={task.sample_network_approved}
        by={task.sample_network_by}
        canEdit={isEditor || canApprove("network")}
        pending={sampleApproval.isPending}
        onSetApproved={setGate("network")}
      />

      <div style={{ marginTop: 12 }}>
        <div className={styles.sectionLabel}>Фото образца</div>
        <DocumentList
          code={code}
          stage={6}
          canEdit={isEditor}
          kinds={[{ value: "photo", label: "Фото" }]}
        />
      </div>
    </div>
  );
}

function ShipmentStage({ task, code, isEditor, updateTask, setError }: StageContentProps) {
  const [orderNo, setOrderNo] = useState(task.shipment_order_no);
  const addComment = useAddComment(code);
  const [requested, setRequested] = useState(false);

  async function saveOrderNo() {
    try {
      await updateTask.mutateAsync({ shipment_order_no: orderNo });
    } catch (e) {
      setError(apiErrorMessage(e, "Не удалось сохранить номер заказа"));
    }
  }

  function requestOrderNo() {
    setError("");
    addComment.mutate("Запрошен номер отгрузки у менеджера.", {
      onSuccess: () => setRequested(true),
      onError: (e) => setError(apiErrorMessage(e, "Не удалось отправить запрос")),
    });
  }

  return (
    <div>
      <div className={forms.row}>
        <label className={forms.label}>Номер отгрузки</label>
        {isEditor ? (
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <input
              className={forms.input}
              value={orderNo}
              onChange={(e) => setOrderNo(e.target.value)}
              onBlur={saveOrderNo}
            />
            <Button variant="ghost" disabled={addComment.isPending} onClick={requestOrderNo}>
              Запросить
            </Button>
            {requested && (
              <span style={{ fontSize: 11, color: "var(--accent3)" }}>✓ запрос отправлен</span>
            )}
          </div>
        ) : (
          <div className={styles.fieldValue}>{orderNo || "—"}</div>
        )}
      </div>

      <div style={{ marginTop: 12 }}>
        <div className={styles.sectionLabel}>Отгрузочные документы</div>
        <DocumentList
          code={code}
          stage={7}
          canEdit={isEditor}
          kinds={[
            { value: "waybill", label: "Накладная" },
            { value: "registry", label: "Реестр" },
          ]}
        />
      </div>
    </div>
  );
}

function FinalStage({ code, task, isEditor, setStageApproval, setError }: StageContentProps) {
  async function checkReady() {
    setError("");
    try {
      const result = await setStageApproval.mutateAsync({
        stage: FINAL_APPROVAL_STAGE,
        approved: true,
      });
      if (result.blocked_reasons.length > 0) {
        setError("Нельзя закрыть: " + result.blocked_reasons.join("; "));
      }
    } catch (e) {
      setError(apiErrorMessage(e, "Не удалось проверить готовность"));
    }
  }

  return (
    <div>
      <div className={styles.sectionLabel}>Распределение по торговым точкам</div>
      <DeliveriesList code={code} />
      {isEditor && (
        <div style={{ marginTop: 12 }}>
          <Button variant="ghost" disabled={setStageApproval.isPending} onClick={checkReady}>
            Проверить готовность к закрытию
          </Button>
        </div>
      )}
      {task.blocked_reasons.length > 0 && (
        <div style={{ marginTop: 8, fontSize: 11, color: "var(--warn)" }}>
          {task.blocked_reasons.join("; ")}
        </div>
      )}
    </div>
  );
}
