import { useQuery } from "@tanstack/react-query";

import { api } from "../client";

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
