import { useQuery } from "@tanstack/react-query";

import { api } from "../client";

export function useTT() {
  return useQuery({
    queryKey: ["tt"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/tt");
      if (error) throw error;
      return data;
    },
  });
}
