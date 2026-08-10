/** Parses the "дд.мм.гг" strings the backend pre-formats date fields into
 * (see backend/app/serializers.py's _fmt_date, `%d.%m.%y`) — these are
 * display strings, not ISO dates, so `new Date(s)` can't parse them
 * directly. Returns a timestamp, or null if `s` is empty/unparseable. */
export function parseRuDate(s: string | null | undefined): number | null {
  if (!s) return null;
  const m = /^(\d{2})\.(\d{2})\.(\d{2})$/.exec(s);
  if (!m) return null;
  const [, dd, mm, yy] = m;
  const date = new Date(2000 + Number(yy), Number(mm) - 1, Number(dd));
  return Number.isFinite(date.getTime()) ? date.getTime() : null;
}

/** Converts the same "дд.мм.гг" display string to "yyyy-mm-dd", the format
 * `<input type="date">` needs for its `value`. Formats directly from the
 * parsed digits rather than round-tripping through `Date`/`toISOString()`,
 * which shifts the date by the local UTC offset. */
export function ruDateToIso(s: string | null | undefined): string {
  if (!s) return "";
  const m = /^(\d{2})\.(\d{2})\.(\d{2})$/.exec(s);
  if (!m) return "";
  const [, dd, mm, yy] = m;
  return `20${yy}-${mm}-${dd}`;
}
