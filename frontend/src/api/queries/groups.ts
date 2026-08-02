import { useQuery } from "@tanstack/react-query";

import { api } from "../client";

export function useGroups() {
  return useQuery({
    queryKey: ["groups"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/groups");
      if (error) throw error;
      return data;
    },
  });
}
