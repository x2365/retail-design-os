import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../client";
import type { components } from "../schema";

type RetailPointCreate = components["schemas"]["RetailPointCreate"];
type RetailPointUpdate = components["schemas"]["RetailPointUpdate"];
type DeliveryUpdate = components["schemas"]["DeliveryUpdate"];

export function useRetailPoints() {
  return useQuery({
    queryKey: ["retail-points"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/retail-points", {
        params: { query: { page_size: 200 } },
      });
      if (error) throw error;
      return data;
    },
  });
}

function invalidatePoints(queryClient: ReturnType<typeof useQueryClient>) {
  queryClient.invalidateQueries({ queryKey: ["retail-points"] });
  queryClient.invalidateQueries({ queryKey: ["tt"] });
  queryClient.invalidateQueries({ queryKey: ["dashboard"] });
}

export function useCreatePoint() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: RetailPointCreate) => {
      const { error } = await api.POST("/api/retail-points", { body: payload });
      if (error) throw error;
    },
    onSuccess: () => invalidatePoints(queryClient),
  });
}

export function useUpdatePoint() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: RetailPointUpdate }) => {
      const { error } = await api.PATCH("/api/retail-points/{point_id}", {
        params: { path: { point_id: id } },
        body: payload,
      });
      if (error) throw error;
    },
    onSuccess: () => invalidatePoints(queryClient),
  });
}

export function useDeletePoint() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const { error } = await api.DELETE("/api/retail-points/{point_id}", {
        params: { path: { point_id: id } },
      });
      if (error) throw error;
    },
    onSuccess: () => invalidatePoints(queryClient),
  });
}

export function usePointDeliveries(pointId: number | null) {
  return useQuery({
    queryKey: ["retail-points", pointId, "deliveries"],
    enabled: pointId !== null,
    queryFn: async () => {
      const { data, error } = await api.GET("/api/retail-points/{point_id}/deliveries", {
        params: { path: { point_id: pointId! } },
      });
      if (error) throw error;
      return data;
    },
  });
}

export function useUpdatePointDelivery(pointId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: DeliveryUpdate }) => {
      const { error } = await api.PATCH("/api/deliveries/{delivery_id}", {
        params: { path: { delivery_id: id } },
        body: payload,
      });
      if (error) throw error;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["retail-points", pointId, "deliveries"] });
      invalidatePoints(queryClient);
    },
  });
}
