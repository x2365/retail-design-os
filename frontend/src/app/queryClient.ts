import { QueryClient } from "@tanstack/react-query";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
      // Refetch-on-focus firing right as the browser's own page-translate
      // feature has rewritten the DOM makes React reconcile against DOM
      // nodes it no longer recognizes (translate has reparented them) —
      // a well-known React+in-page-translation crash class. Switching to
      // the browser's translate menu and back is exactly a focus/blur
      // cycle, so this is a real trigger here, not a hypothetical one.
      refetchOnWindowFocus: false,
    },
  },
});
