import { useMutation, useQuery } from "@tanstack/react-query";

import { api } from "../client";

export function useAssistantStatus() {
  return useQuery({
    queryKey: ["assistant", "status"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/assistant/status");
      if (error) throw error;
      return data;
    },
    staleTime: Infinity,
  });
}

export function useAskAssistant() {
  return useMutation({
    mutationFn: async ({ query, screen }: { query: string; screen: string }) => {
      const { data, error } = await api.POST("/api/assistant", { body: { query, screen } });
      if (error) throw error;
      return data;
    },
  });
}
