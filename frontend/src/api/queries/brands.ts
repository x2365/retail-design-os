import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../client";
import type { components } from "../schema";

type BrandCreate = components["schemas"]["BrandCreate"];
type BrandUpdate = components["schemas"]["BrandUpdate"];

export function useBrands() {
  return useQuery({
    queryKey: ["brands"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/brands");
      if (error) throw error;
      return data;
    },
  });
}

function invalidateBrands(queryClient: ReturnType<typeof useQueryClient>) {
  queryClient.invalidateQueries({ queryKey: ["brands"] });
  queryClient.invalidateQueries({ queryKey: ["dashboard"] });
}

export function useCreateBrand() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: BrandCreate) => {
      const { error } = await api.POST("/api/brands", { body: payload });
      if (error) throw error;
    },
    onSuccess: () => invalidateBrands(queryClient),
  });
}

export function useUpdateBrand() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: BrandUpdate }) => {
      const { error } = await api.PATCH("/api/brands/{brand_id}", {
        params: { path: { brand_id: id } },
        body: payload,
      });
      if (error) throw error;
    },
    onSuccess: () => invalidateBrands(queryClient),
  });
}

export function useDeleteBrand() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const { error } = await api.DELETE("/api/brands/{brand_id}", {
        params: { path: { brand_id: id } },
      });
      if (error) throw error;
    },
    onSuccess: () => invalidateBrands(queryClient),
  });
}
