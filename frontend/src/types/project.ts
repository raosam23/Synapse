export enum ProjectStatus {
    PLANNING = "planning",
    ACTIVE = "active",
    COMPLETED = "completed",
    CANCELLED = "cancelled",
}

export interface Project {
    id: string;
    name: string;
    requirements: string;
    duration_weeks: number;
    sprint_length_weeks: number;
    ai_opinion: string | null;
    status: ProjectStatus;
    created_by_id: string;
    created_at: string;
    updated_at: string;
}

export interface CreateProject {
    name: string;
    requirements: string;
    duration_weeks: number;
}

export interface UpdateProject {
    name?: string;
    requirements?: string;
    duration_weeks?: number;
    status?: ProjectStatus;
}
