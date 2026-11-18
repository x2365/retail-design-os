import { lang, locale, t } from "../i18n";
/** Money formatting — ported from the old app's fmtMln/fmtMoneyShort so
 * dashboard/budget numbers read identically (₽1,2 млн / ₽340 тыс / ₽900).
 * All API money fields are kopecks; callers must convert with kopToRub(). */

export function kopToRub(kopecks: number): number {
  return (kopecks || 0) / 100;
}

function shorten(rub: number): string {
  const v = Math.round(rub || 0);
  const a = Math.abs(v);
  if (a >= 1e6) {
    const m = (v / 1e6).toFixed(1).replace(".0", "");
    return (lang === "ru" ? m.replace(".", ",") : m) + t(" млн");
  }
  if (a >= 1e3) return Math.round(v / 1e3).toLocaleString(locale) + t(" тыс");
  return v.toLocaleString(locale);
}

/** "₽1,2 млн" — for standalone KPI values. */
export function formatMoney(rub: number): string {
  return "₽" + shorten(rub);
}

/** "1,2 млн" (no currency symbol) — for "X / Y ₽" pair displays. */
export function formatMoneyShort(rub: number): string {
  return shorten(rub);
}
