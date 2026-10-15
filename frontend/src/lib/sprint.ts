import { api } from "./api";
import { Sprint, CreateSprint } from "@/types/sprint";

export const sprintApi = {
    list: (projectId: string) => api.get<Sprint[]>(`/api/v1/sprints?project_id=${projectId}`),
    create: (data: CreateSprint) => api.post<Sprint[]>("/api/v1/sprints/", data),
}
