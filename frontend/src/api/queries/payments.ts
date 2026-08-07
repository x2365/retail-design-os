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

export function useUpdatePaymentStatus() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ code, paymentStatus }: { code: string; paymentStatus: string }) => {
      const { error } = await api.PATCH("/api/tasks/{code}", {
        params: { path: { code } },
        body: { payment_status: paymentStatus },
      });
      if (error) throw error;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["payments"] });
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}
