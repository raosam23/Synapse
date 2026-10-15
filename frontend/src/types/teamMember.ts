export interface TeamMember {
    id: string;
    name: string;
    skills: string[];
    user_id: string | null;
    project_id: string;
}

export interface CreateTeamMember {
    user_id: string;
    project_id: string;
    skills: string[];
}
