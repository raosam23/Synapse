import { create } from "zustand";
import { projectApi } from "@/lib/project";
import { Project, CreateProject, UpdateProject } from "@/types/project";

interface ProjectState {
    projects: Project[];
    currentProject: Project | null;
    isLoading: boolean;
    error: string | null;

    loadProjects: () => Promise<void>;
    loadProject: (id: string) => Promise<void>;
    createProject: (data: CreateProject) => Promise<void>;
    updateProject: (id: string, data: UpdateProject) => Promise<void>;
    deleteProject: (id: string) => Promise<void>;
    clearError: () => void;
}

export const useProjectStore = create<ProjectState>((set) => ({
    projects: [],
    currentProject: null,
    isLoading: false,
    error: null,

    loadProjects: async () => {
        set({isLoading: true, error: null})
        try {
            const projects = await projectApi.list();
            set({projects});
        } catch (error: unknown) {
            set({error: error instanceof Error ? error.message : "An unknown error occurred"});
            throw error;
        } finally {
            set({isLoading: false});
        }
    },
    loadProject: async (id) => {
        set({isLoading: true, error: null})
        try {
            const project = await projectApi.get(id);
            set({currentProject: project});
        }
        catch (error: unknown) {
            set({error: error instanceof Error ? error.message : "An unknown error occurred"});
            throw error;
        } finally {
            set({isLoading: false});
        }
    },
    createProject: async (data) => {
        set({isLoading: true, error: null})
        try {
            const project = await projectApi.create(data);
            set((state) => ({projects: [...state.projects, project]}));
            set({currentProject: project});
        } catch(error: unknown) {
            set({error: error instanceof Error ? error.message : "An unknown error occurred"});
            throw error;
        } finally {
            set({isLoading: false});
        }
    },
    updateProject: async (id, data) => {
        set({isLoading: true, error: null});
        try {
            const updatedProject = await projectApi.update(id, data);
            set((state) => ({projects: state.projects.map((project) => project.id === id ? updatedProject : project)}));
            set({currentProject: updatedProject});
        } catch(error: unknown) {
            set({error: error instanceof Error ? error.message : "An unknown error occurred"});
            throw error;
        } finally {
            set({isLoading: false});
        }
    },
    deleteProject: async (id) => {
        set({isLoading: true, error: null});
        try {
            await projectApi.delete(id);
            set((state) => ({projects: state.projects.filter((project) => project.id !== id)}));
            set({currentProject: null});
        } catch(error: unknown) {
            set({error: error instanceof Error ? error.message : "An unknown error occurred"});
            throw error;
        } finally {
            set({isLoading: false});
        }
    },
    clearError: () => set({error: null}),
}));