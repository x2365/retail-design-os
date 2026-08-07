import { useEffect, useState } from "react";

import { fetchAuthedBlobUrl } from "../../api/client";

export function DocumentPreview({
  downloadUrl,
  filename,
}: {
  downloadUrl: string;
  filename: string;
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
