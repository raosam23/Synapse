export enum TaskStatus {
    BACKLOG = "backlog",
    TODO = "todo",
    DOING = "doing",
    DONE = "done",
}

export interface Task {
    id: string;
    title: string;
    description: string | null;
    status: TaskStatus;
    sprint_id: string | null;
    assignee_id: string | null;
    story_points: number | null;
    risk_flag: boolean | null;
    created_by_id: string | null;
    project_id: string;
    created_at: string;
    updated_at: string;
}
