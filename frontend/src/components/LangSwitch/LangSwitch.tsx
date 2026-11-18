import { lang, setLang, type Lang } from "../../i18n";
import styles from "./LangSwitch.module.css";

const OPTIONS: Lang[] = ["ru", "en"];

/** RU | EN segmented toggle. Switching saves the choice and reloads the page. */
export function LangSwitch({ className }: { className?: string }) {
  return (
    <div
      className={[styles.wrap, className].filter(Boolean).join(" ")}
      role="group"
      aria-label="Language"
    >
      {OPTIONS.map((l) => (
        <button
          key={l}
          type="button"
          className={l === lang ? `${styles.opt} ${styles.active}` : styles.opt}
          aria-pressed={l === lang}
          onClick={() => l !== lang && setLang(l)}
        >
          {l.toUpperCase()}
        </button>
      ))}
    </div>
  );
}
