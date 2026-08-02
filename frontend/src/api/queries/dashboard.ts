import { useQuery } from "@tanstack/react-query";

import { api } from "../client";

export function useDashboardKpis() {
  return useQuery({
    queryKey: ["dashboard", "kpis"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/dashboard/kpis");
      if (error) throw error;
      return data;
    },
  });
}
