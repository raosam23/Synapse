"use client";

import { useEffect } from "react";
import Link from "next/link";

import { useProjectStore } from "@/store/projectStore";

const ProjectsPage = () => {
  const { projects, isLoading, error, loadProjects } = useProjectStore();
  useEffect(() => {
    loadProjects();
  }, [loadProjects]);
  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;
  return (
    <div>
      <h1>Projects</h1>
      <div>
        <Link href="/projects/new">Create New Project</Link>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {projects.length === 0 ? (
          <div>No projects found. Create one to get started</div>
        ) : (
          projects.map((project) => (
            <Link key={project.id} href={`/projects/${project.id}`}>
              <div>
                <h3>{project.name}</h3>
                <p>Status: {project.status}</p>
                <p>Duration: {project.duration_weeks} weeks</p>
                {project.ai_opinion && <p>AI Opinion: {project.ai_opinion}</p>}
              </div>
            </Link>
          ))
        )}
      </div>
    </div>
  );
};

export default ProjectsPage;
