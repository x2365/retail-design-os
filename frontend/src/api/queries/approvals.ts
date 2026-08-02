import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../client";

export function useApprovals(status: "pending" | "all" = "all") {
  return useQuery({
    queryKey: ["approvals", status],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/approvals", { params: { query: { status } } });
      if (error) throw error;
      return data;
    },
  });
}

export function useApproveApproval() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const { error } = await api.POST("/api/approvals/{approval_id}/approve", {
        params: { path: { approval_id: id } },
      });
      if (error) throw error;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["approvals"] }),
  });
}

export function useRejectApproval() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const { error } = await api.POST("/api/approvals/{approval_id}/reject", {
        params: { path: { approval_id: id } },
      });
      if (error) throw error;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["approvals"] }),
  });
}
