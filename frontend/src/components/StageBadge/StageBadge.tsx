import styles from "./StageBadge.module.css";

/** Buckets the 12-stage pipeline into 6 colors — ported from the old app's
 * stageClass(). Colors cycle every 2 stages so the badge stays readable
 * without needing 12 distinct hues. */
function colorBucket(stage: number): 1 | 2 | 3 | 4 | 5 | 6 {
  if (stage <= 2) return 1;
  if (stage <= 4) return 2;
  if (stage <= 6) return 3;
  if (stage <= 8) return 4;
  if (stage <= 10) return 5;
  return 6;
}

export function StageBadge({ stage, label }: { stage: number; label: string }) {
  const n = colorBucket(stage);
  return <span className={[styles.stage, styles[`s${n}`]].join(" ")}>{label}</span>;
}
