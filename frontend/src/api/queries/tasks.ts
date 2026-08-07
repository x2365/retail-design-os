import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../client";
import type { components } from "../schema";

type TaskCreate = components["schemas"]["TaskCreate"];

interface UseTasksParams {
  group?: string;
  band?: string;
  urgent?: boolean;
  search?: string;
  page?: number;
  page_size?: number;
}

export function useTasks(params: UseTasksParams = {}) {
  return useQuery({
    queryKey: ["tasks", params],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/tasks", { params: { query: params } });
      if (error) throw error;
      return data;
    },
  });
}

export function useCreateTask() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: TaskCreate) => {
      const { data, error } = await api.POST("/api/tasks", { body: payload });
      if (error) throw error;
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}
