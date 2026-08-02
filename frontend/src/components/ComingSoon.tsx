/** Placeholder for routes whose feature view hasn't landed yet as the
 * frontend rewrite proceeds screen-by-screen. Every nav item is clickable
 * and demoable from the first shell commit onward, even before its real
 * content exists. */
export function ComingSoon({ title }: { title: string }) {
  return (
    <div style={{ color: "var(--text2)", fontSize: 13 }}>
      <p style={{ marginBottom: 8 }}>«{title}» — экран в разработке.</p>
    </div>
  );
}
