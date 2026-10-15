import { api } from "./api";
import { Project, CreateProject, UpdateProject } from "../types/project";

export const projectApi = {
    list: async () => api.get<Project[]>("/api/v1/projects"),

    get: async (id: string) => api.get<Project>(`/api/v1/projects/${id}`),

    create: (data: CreateProject) => api.post<Project>("/api/v1/projects", data),

    update: (id: string, data: UpdateProject) => api.put<Project>(`/api/v1/projects/${id}`, data),

    delete: (id: string) => api.delete<void>(`/api/v1/projects/${id}`),

    runAnalysis: (projectId: string) => api.post(`/api/v1/projects/${projectId}/agents/run`, {}),

    planSprint: (projectId: string) => api.post(`/api/v1/projects/${projectId}/agents/plan-sprint`, {}),

    analyzeRisks: (projectId: string) => api.post(`/api/v1/projects/${projectId}/agents/analyze-risk`, {}),

    createSprints: (projectId: string) => api.post(`/api/v1/sprints/`, { project_id: projectId }),
};