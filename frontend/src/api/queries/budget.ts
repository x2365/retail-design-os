import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../client";

export function useBudgetLog() {
  return useQuery({
    queryKey: ["budget", "log"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/budget/log");
      if (error) throw error;
      return data;
    },
  });
}

export function useSaveGroupPlan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ code, budgetPlannedKop }: { code: string; budgetPlannedKop: number }) => {
      const { error } = await api.PATCH("/api/groups/{code}/budget", {
        params: { path: { code } },
        body: { budget_planned: budgetPlannedKop },
      });
      if (error) throw error;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["groups"] });
      queryClient.invalidateQueries({ queryKey: ["budget", "log"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}
