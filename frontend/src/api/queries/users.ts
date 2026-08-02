import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../client";
import type { components } from "../schema";

type UserCreate = components["schemas"]["UserCreate"];
type UserUpdate = components["schemas"]["UserUpdate"];

export function useUsers() {
  return useQuery({
    queryKey: ["users"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/users");
      if (error) throw error;
      return data;
    },
  });
}

function invalidateUsers(queryClient: ReturnType<typeof useQueryClient>) {
  queryClient.invalidateQueries({ queryKey: ["users"] });
}

export function useCreateUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: UserCreate) => {
      const { error } = await api.POST("/api/users", { body: payload });
      if (error) throw error;
    },
    onSuccess: () => invalidateUsers(queryClient),
  });
}

export function useUpdateUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: UserUpdate }) => {
      const { error } = await api.PATCH("/api/users/{user_id}", {
        params: { path: { user_id: id } },
        body: payload,
      });
      if (error) throw error;
    },
    onSuccess: () => invalidateUsers(queryClient),
  });
}

export function useResetUserPassword() {
  return useMutation({
    mutationFn: async ({ id, newPassword }: { id: number; newPassword: string }) => {
      const { error } = await api.POST("/api/users/{user_id}/password", {
        params: { path: { user_id: id } },
        body: { new_password: newPassword },
      });
      if (error) throw error;
    },
  });
}

export function useChangeMyPassword() {
  return useMutation({
    mutationFn: async ({
      currentPassword,
      newPassword,
    }: {
      currentPassword: string;
      newPassword: string;
    }) => {
      const { error } = await api.POST("/api/me/password", {
        body: { current_password: currentPassword, new_password: newPassword },
      });
      if (error) throw error;
    },
  });
}
