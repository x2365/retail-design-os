import { colorBucket } from "../../lib/stages";
import styles from "./StageBadge.module.css";

export function StageBadge({ stage, label }: { stage: number; label: string }) {
  const n = colorBucket(stage);
  return <span className={[styles.stage, styles[`s${n}`]].join(" ")}>{label}</span>;
}
