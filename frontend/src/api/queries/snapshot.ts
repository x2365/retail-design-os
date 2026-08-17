import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../client";

export function useSnapshot() {
  return useQuery({
    queryKey: ["snapshot"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/internal/snapshot");
      if (error) throw error;
      return data;
    },
  });
}

export function useTakeSnapshot() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data, error } = await api.POST("/api/internal/snapshot/take");
      if (error) throw error;
      return data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["snapshot"] }),
  });
}

export function useRestoreSnapshot() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data, error } = await api.POST("/api/internal/snapshot/restore");
      if (error) throw error;
      return data;
    },
    onSuccess: () => queryClient.invalidateQueries(),
  });
}
