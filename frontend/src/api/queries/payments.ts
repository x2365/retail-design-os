import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../client";
import type { components } from "../schema";

type PaymentUpsert = components["schemas"]["PaymentUpsert"];

export function usePayments() {
  return useQuery({
    queryKey: ["payments"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/payments");
      if (error) throw error;
      return data;
    },
  });
}

export function useUpsertPayment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: PaymentUpsert) => {
      const { error } = await api.POST("/api/payments", { body: payload });
      if (error) throw error;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["payments"] }),
  });
}
