import { api } from "./api";
import { TeamMember, CreateTeamMember } from "@/types/teamMember";

export const teamMemberApi = {
    list: (projectId: string) => api.get<TeamMember[]>(`/api/v1/team-members?project_id=${projectId}`),

    create: (data: CreateTeamMember) => api.post<TeamMember>("/api/v1/team-members", data),
}
