export interface Sprint {
    id: string;
    project_id: string;
    index: number;
    start_date: string;
    end_date: string;
}

export interface CreateSprint {
    project_id: string;
    start_date: string;
}
