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
   * "thumb" — inline thumbnail for a file-list row.
   * "cover" — full-width banner (e.g. equipment card cover photo). */
  size?: "large" | "thumb" | "cover";
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
            width: 96,
            height: 96,
            borderRadius: 8,
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
        style={{ width: 96, height: 96, objectFit: "cover", borderRadius: 8, display: "block" }}
      />
    );
  }

  if (size === "cover") {
    if (!src) {
      return (
        <span
          style={{
            width: "100%",
            height: 160,
            borderRadius: "10px 10px 0 0",
            background: "var(--surface3)",
            display: "block",
          }}
        />
      );
    }
    return (
      <img
        src={src}
        alt={filename}
        style={{
          width: "100%",
          height: 160,
          objectFit: "cover",
          borderRadius: "10px 10px 0 0",
          display: "block",
        }}
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
