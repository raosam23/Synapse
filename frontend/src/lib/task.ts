import { api } from "./api";
import { Task, TaskStatus } from "../types/task";

export const taskApi = {
    list: (projectId: string) => api.get<Task[]>(`/api/v1/tasks/?project_id=${projectId}`),
    update: (id: string, data: {status: TaskStatus}) => api.put<Task>(`/api/v1/tasks/${id}`, data),
};