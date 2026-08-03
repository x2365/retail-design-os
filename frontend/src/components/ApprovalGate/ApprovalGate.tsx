import { Badge } from "../Badge/Badge";
import { Button } from "../Button/Button";
import styles from "./ApprovalGate.module.css";

interface ApprovalGateProps {
  label: string;
  approved: boolean;
  by?: string;
  canEdit: boolean;
  pending?: boolean;
  onSetApproved: (approved: boolean) => void;
}

/** The "кто/когда согласовал" checkbox pattern used across every approval
 * gate (prep brand/network, KP manager/director/network, sample QC/brand/
 * network) — ported from the old app's inline `gate()` helper in
 * renderPrep/renderKp/renderSample. */
export function ApprovalGate({
  label,
  approved,
  by,
  canEdit,
  pending,
  onSetApproved,
}: ApprovalGateProps) {
  if (!canEdit) {
    return (
      <div className={styles.row}>
        <Badge color={approved ? "green" : "amber"}>
          {approved ? `✓ ${label}: согласовано` : `${label}: не согласовано`}
        </Badge>
      </div>
    );
  }

  if (approved) {
    return (
      <div className={styles.row}>
        <Badge color="green">✓ {label}: согласовано</Badge>
        {by && <span className={styles.by}>{by}</span>}
        <Button variant="ghost" disabled={pending} onClick={() => onSetApproved(false)}>
          снять
        </Button>
      </div>
    );
  }

  return (
    <div className={styles.row}>
      <span className={styles.label}>{label}</span>
      <span className={styles.pendingLabel}>не согласовано</span>
      <button className={styles.approveBtn} disabled={pending} onClick={() => onSetApproved(true)}>
        Согласовано
      </button>
    </div>
  );
}
