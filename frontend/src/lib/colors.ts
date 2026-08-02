/** Group accent colors — ported from the old app's groupColor(). Group.color
 * from the API is the source of truth where available (brand/budget panels);
 * this fallback covers spots that only know the group code (task cards). */
export function groupColor(code: string): string {
  if (code === "A") return "#5b6af0";
  if (code === "B") return "#06d6a0";
  return "#f59e0b";
}
