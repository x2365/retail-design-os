import { useEffect, useState } from "react";

import { fetchAuthedBlobUrl } from "../../api/client";

export function DocumentPreview({
  downloadUrl,
  filename,
  size = "large",
}: {
  downloadUrl: string;
  filename: string;
  /** "large" — featured preview (e.g. the sketch on «Согласования»).
   * "thumb" — small inline thumbnail for a file-list row. */
  size?: "large" | "thumb";
}) {
  const [src, setSrc] = useState<string | null>(null);

  useEffect(() => {
    let objectUrl: string | null = null;
    let cancelled = false;
    fetchAuthedBlobUrl(downloadUrl).then((url) => {
      if (cancelled) {
        URL.revokeObjectURL(url);
        return;
      }
      objectUrl = url;
      setSrc(url);
    });
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [downloadUrl]);

  if (size === "thumb") {
    if (!src) {
      return (
        <span
          style={{
            width: 36,
            height: 36,
            borderRadius: 6,
            background: "var(--surface3)",
            display: "inline-block",
          }}
        />
      );
    }
    return (
      <img
        src={src}
        alt={filename}
        style={{ width: 36, height: 36, objectFit: "cover", borderRadius: 6, display: "block" }}
      />
    );
  }

  if (!src) {
    return <span style={{ fontSize: 11, color: "var(--text3)" }}>Загрузка превью…</span>;
  }
  return (
    <img
      src={src}
      alt={filename}
      style={{ maxWidth: "100%", maxHeight: 240, borderRadius: 8, display: "block" }}
    />
  );
}
