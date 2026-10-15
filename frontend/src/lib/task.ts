import { api } from "./api";
import { Task } from "../types/task";

export const taskApi = {
    list: (projectId: string) => api.get<Task[]>(`/api/v1/tasks/?project_id=${projectId}`),
};