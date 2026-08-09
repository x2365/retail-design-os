import { useQuery } from "@tanstack/react-query";

import { api } from "../client";

export function useMetrics() {
  return useQuery({
    queryKey: ["metrics"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/metrics");
      if (error) throw error;
      return data;
    },
  });
}
