import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../client";
import type { components } from "../schema";

type TaskUpdate = components["schemas"]["TaskUpdate"];
type DeliveryUpdate = components["schemas"]["DeliveryUpdate"];
type ContractorCreate = components["schemas"]["ContractorCreate"];

function invalidateTask(queryClient: ReturnType<typeof useQueryClient>, code: string) {
  queryClient.invalidateQueries({ queryKey: ["task", code] });
  queryClient.invalidateQueries({ queryKey: ["tasks"] });
  queryClient.invalidateQueries({ queryKey: ["dashboard"] });
}

export function useTask(code: string) {
  return useQuery({
    queryKey: ["task", code],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/tasks/{code}", { params: { path: { code } } });
      if (error) throw error;
      return data;
    },
  });
}

export function useUpdateTask(code: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: TaskUpdate) => {
      const { data, error } = await api.PATCH("/api/tasks/{code}", {
        params: { path: { code } },
        body: payload,
      });
      if (error) throw error;
      return data;
    },
    onSuccess: () => invalidateTask(queryClient, code),
  });
}

export function useSetStageApproval(code: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { stage: number; approved: boolean }) => {
      const { data, error } = await api.PATCH("/api/tasks/{code}/stage-approval", {
        params: { path: { code } },
        body: payload,
      });
      if (error) throw error;
      return data;
    },
    onSuccess: () => invalidateTask(queryClient, code),
  });
}

export function useTaskHistory(code: string) {
  return useQuery({
    queryKey: ["task", code, "history"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/tasks/{code}/history", {
        params: { path: { code } },
      });
      if (error) throw error;
      return data;
    },
  });
}

export function useUpdateDelivery(code: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: DeliveryUpdate }) => {
      const { error } = await api.PATCH("/api/deliveries/{delivery_id}", {
        params: { path: { delivery_id: id } },
        body: payload,
      });
      if (error) throw error;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["task", code, "deliveries"] }),
  });
}

export function useTaskDeliveries(code: string) {
  return useQuery({
    queryKey: ["task", code, "deliveries"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/tasks/{code}/deliveries", {
        params: { path: { code } },
      });
      if (error) throw error;
      return data;
    },
  });
}

export function useTaskComments(code: string) {
  return useQuery({
    queryKey: ["task", code, "comments"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/tasks/{code}/comments", {
        params: { path: { code } },
      });
      if (error) throw error;
      return data;
    },
  });
}

export function useAddComment(code: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (text: string) => {
      const { error } = await api.POST("/api/tasks/{code}/comments", {
        params: { path: { code } },
        body: { text },
      });
      if (error) throw error;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["task", code, "comments"] }),
  });
}

export function usePrepApproval(code: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { gate: string; approved: boolean; comment?: string }) => {
      const { error } = await api.POST("/api/tasks/{code}/prep-approval", {
        params: { path: { code } },
        body: { ...payload, comment: payload.comment ?? "" },
      });
      if (error) throw error;
    },
    onSuccess: () => invalidateTask(queryClient, code),
  });
}

export function useKpApproval(code: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { gate: string; approved: boolean }) => {
      const { error } = await api.POST("/api/tasks/{code}/kp-approval", {
        params: { path: { code } },
        body: payload,
      });
      if (error) throw error;
    },
    onSuccess: () => invalidateTask(queryClient, code),
  });
}

export function useSampleApproval(code: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { gate?: string | null; approved: boolean }) => {
      const { error } = await api.POST("/api/tasks/{code}/sample-approval", {
        params: { path: { code } },
        body: payload,
      });
      if (error) throw error;
    },
    onSuccess: () => invalidateTask(queryClient, code),
  });
}

export function useAssignTeam(code: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (members: { name: string; email?: string; telegram?: string }[]) => {
      const { error } = await api.POST("/api/tasks/{code}/team", {
        params: { path: { code } },
        body: {
          members: members.map((m) => ({
            name: m.name,
            email: m.email ?? "",
            telegram: m.telegram ?? "",
          })),
        },
      });
      if (error) throw error;
    },
    onSuccess: () => invalidateTask(queryClient, code),
  });
}

export function useTaskDocuments(code: string, stage?: number) {
  return useQuery({
    queryKey: ["task", code, "documents", stage],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/tasks/{code}/documents", {
        params: { path: { code }, query: stage ? { stage } : {} },
      });
      if (error) throw error;
      return data;
    },
  });
}

export function useUploadDocument(code: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ file, kind, stage }: { file: File; kind: string; stage?: number }) => {
      const form = new FormData();
      form.append("file", file);
      form.append("kind", kind);
      if (stage) form.append("stage", String(stage));
      // openapi-fetch detects a FormData body and skips JSON-serializing it
      // (the browser sets the multipart Content-Type + boundary); the schema
      // types this as `{file: string}` because OpenAPI has no FormData type.
      const { error } = await api.POST("/api/tasks/{code}/documents", {
        params: { path: { code } },
        body: form as unknown as { file: string; kind: string; stage?: number | null },
      });
      if (error) throw error;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["task", code, "documents"] });
      invalidateTask(queryClient, code);
    },
  });
}

export function useDeleteDocument(code: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (docId: number) => {
      const { error } = await api.DELETE("/api/documents/{doc_id}", {
        params: { path: { doc_id: docId } },
      });
      if (error) throw error;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["task", code, "documents"] }),
  });
}

export function useContractors() {
  return useQuery({
    queryKey: ["contractors"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/contractors");
      if (error) throw error;
      return data;
    },
  });
}

export function useCreateContractor() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: ContractorCreate) => {
      const { data, error } = await api.POST("/api/contractors", { body: payload });
      if (error) throw error;
      return data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["contractors"] }),
  });
}

export function useNomenclature(code: string) {
  return useQuery({
    queryKey: ["task", code, "nomenclature"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/tasks/{code}/nomenclature", {
        params: { path: { code } },
      });
      if (error) throw error;
      return data;
    },
  });
}

export function useAddNomenclature(code: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      sku?: string;
      barcode?: string;
      name?: string;
      qty?: number;
    }) => {
      const { error } = await api.POST("/api/tasks/{code}/nomenclature", {
        params: { path: { code } },
        body: {
          sku: payload.sku ?? "",
          barcode: payload.barcode ?? "",
          name: payload.name ?? "",
          qty: payload.qty ?? 0,
        },
      });
      if (error) throw error;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["task", code, "nomenclature"] }),
  });
}
