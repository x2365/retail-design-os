import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../client";
import type { components } from "../schema";

type EquipmentCreate = components["schemas"]["EquipmentCreate"];
type EquipmentUpdate = components["schemas"]["EquipmentUpdate"];

export function useEquipment(q?: string) {
  return useQuery({
    queryKey: ["equipment", q ?? ""],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/equipment", {
        params: { query: q ? { q } : {} },
      });
      if (error) throw error;
      return data;
    },
  });
}

function invalidateEquipment(queryClient: ReturnType<typeof useQueryClient>) {
  queryClient.invalidateQueries({ queryKey: ["equipment"] });
}

export function useCreateEquipment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: EquipmentCreate) => {
      const { error } = await api.POST("/api/equipment", { body: payload });
      if (error) throw error;
    },
    onSuccess: () => invalidateEquipment(queryClient),
  });
}

export function useUpdateEquipment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: EquipmentUpdate }) => {
      const { error } = await api.PATCH("/api/equipment/{eq_id}", {
        params: { path: { eq_id: id } },
        body: payload,
      });
      if (error) throw error;
    },
    onSuccess: () => invalidateEquipment(queryClient),
  });
}

export function useDeleteEquipment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const { error } = await api.DELETE("/api/equipment/{eq_id}", {
        params: { path: { eq_id: id } },
      });
      if (error) throw error;
    },
    onSuccess: () => invalidateEquipment(queryClient),
  });
}

export function useProduceEquipment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const { data, error } = await api.POST("/api/equipment/{eq_id}/produce", {
        params: { path: { eq_id: id } },
        body: { team: [], tt_total: 0 },
      });
      if (error) throw error;
      return data;
    },
    onSuccess: () => {
      invalidateEquipment(queryClient);
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export function useEquipmentDocuments(eqId: number | null) {
  return useQuery({
    queryKey: ["equipment", eqId, "documents"],
    enabled: eqId !== null,
    queryFn: async () => {
      const { data, error } = await api.GET("/api/equipment/{eq_id}/documents", {
        params: { path: { eq_id: eqId! } },
      });
      if (error) throw error;
      return data;
    },
  });
}

export function useUploadEquipmentDocument(eqId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ file, kind }: { file: File; kind: string }) => {
      const form = new FormData();
      form.append("file", file);
      form.append("kind", kind);
      const { error } = await api.POST("/api/equipment/{eq_id}/documents", {
        params: { path: { eq_id: eqId! } },
        body: form as unknown as { file: string; kind: string },
      });
      if (error) throw error;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["equipment", eqId, "documents"] }),
  });
}

export function useDeleteEquipmentDocument(eqId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (docId: number) => {
      const { error } = await api.DELETE("/api/documents/{doc_id}", {
        params: { path: { doc_id: docId } },
      });
      if (error) throw error;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["equipment", eqId, "documents"] }),
  });
}
