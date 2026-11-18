/** UI language (RU/EN). Russian strings in the code are the translation keys:
 * `t("Дашборд")` returns the Russian text as-is, or its English version from
 * ./en.ts. The language is fixed for the page's lifetime — picked once at
 * startup (?lang= → saved choice → browser language) — so `t()` is a plain
 * function that also works in module-level constants; switching reloads the
 * page. `npm run i18n:check` (CI) fails on any Cyrillic literal not wrapped in
 * `t()` or any key missing from en.ts. */
import { EN } from "./en";

export type Lang = "ru" | "en";

const STORAGE_KEY = "rd_lang";

function readStored(): Lang | null {
  try {
    const v = localStorage.getItem(STORAGE_KEY);
    return v === "ru" || v === "en" ? v : null;
  } catch {
    return null;
  }
}

function store(l: Lang) {
  try {
    localStorage.setItem(STORAGE_KEY, l);
  } catch {
    /* private mode — the choice just won't persist */
  }
}

function detect(): Lang {
  if (typeof window === "undefined") return "ru";
  const q = new URLSearchParams(window.location.search).get("lang");
  if (q === "ru" || q === "en") {
    store(q);
    return q;
  }
  const saved = readStored();
  if (saved) return saved;
  const langs = navigator.languages?.length ? navigator.languages : [navigator.language];
  return langs.some((l) => l?.toLowerCase().startsWith("ru")) ? "ru" : "en";
}

export const lang: Lang = detect();

/** BCP-47 locale for Intl / toLocale* formatting. */
export const locale = lang === "en" ? "en-GB" : "ru-RU";

if (typeof document !== "undefined") {
  document.documentElement.lang = lang;
  if (lang === "en") document.title = "RetailDesign OS — Equipment tracking";
}

function fill(s: string, params?: Record<string, string | number>): string {
  if (!params) return s;
  return s.replace(/\{(\w+)\}/g, (m, k: string) => (k in params ? String(params[k]) : m));
}

/** Translate a UI string. `{name}` placeholders are filled from `params`.
 * Unknown keys (e.g. text that came from the server) pass through. */
export function t(s: string, params?: Record<string, string | number>): string {
  if (lang === "ru" || !s) return fill(s, params);
  return fill(EN[s] ?? s, params);
}

// Composite backend messages: "<prefix>: reason; reason." — translate the
// prefix and each reason separately so they don't need one key per combination.
const SERVER_PATTERNS: [RegExp, (m: RegExpMatchArray) => string][] = [
  [/^Команда (.+)$/, (m) => t("Команда {name}", { name: m[1] })],
  [
    /^Этап «(.+)» не завершён: (.+?)\.?$/,
    (m) => t("Этап «{stage}» не завершён: {reasons}.", { stage: t(m[1]), reasons: reasons(m[2]) }),
  ],
  [
    /^Нельзя закрыть задачу: (.+?)\.?$/,
    (m) => t("Нельзя закрыть задачу: {reasons}.", { reasons: reasons(m[1]) }),
  ],
  [
    /^Нельзя взять задачу в работу: (.+?)\.?$/,
    (m) => t("Нельзя взять задачу в работу: {reasons}.", { reasons: reasons(m[1]) }),
  ],
];

function reasons(list: string): string {
  return list
    .split("; ")
    .map((r) => {
      const notDelivered = /^не все ТТ доставлены \(не доставлено: (\d+)\)$/.exec(r);
      if (notDelivered)
        return t("не все ТТ доставлены (не доставлено: {n})", { n: notDelivered[1] });
      const unpaid = /^задача не оплачена \(статус: (.+)\)$/.exec(r);
      if (unpaid) return t("задача не оплачена (статус: {status})", { status: t(unpaid[1]) });
      return t(r);
    })
    .join("; ");
}

/** Translate text produced by the backend (labels, error details). */
export function tServer(s: string | null | undefined): string {
  if (!s) return "";
  if (lang === "ru") return s;
  if (s in EN) return EN[s];
  for (const [re, fn] of SERVER_PATTERNS) {
    const m = s.match(re);
    if (m) return fn(m);
  }
  return s;
}

/** Switch language: remember the choice and reload so every label re-renders. */
export function setLang(next: Lang) {
  store(next);
  const url = new URL(window.location.href);
  url.searchParams.delete("lang");
  window.location.replace(url.toString());
}
