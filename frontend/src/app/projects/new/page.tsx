"use client";
import { useState, type SubmitEvent } from "react";
import { useProjectStore } from "@/store/projectStore";
import { useRouter } from "next/navigation";

const NewProjectFields = () => {
  const [formData, setFormData] = useState({
    name: "",
    requirements: "",
    duration_weeks: 0,
  });

  const handleChange = (
    event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
  ) => {
    const { name, value } = event.target as HTMLInputElement;
    setFormData({
      ...formData,
      [name]: name === "duration_weeks" ? Number(value) : value,
    });
  };
  const { createProject, isLoading, error } = useProjectStore();
  const router = useRouter();
  const handleSubmit = async (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    try {
      await createProject(formData);
      const newProject = useProjectStore.getState().currentProject;
      if (newProject) {
        router.push(`/projects/${newProject.id}`);
      } else {
        router.push("/projects");
      }
    } catch (error: unknown) {
      console.error(error);
    }
  };

  if (isLoading) {
    return <div>Loading...</div>;
  }
  if (error) {
    return <div>Error: {error}</div>;
  }
  return (
    <div>
      <h1>New Project</h1>
      <form onSubmit={handleSubmit}>
        <div>
          <label htmlFor="name">Name</label>
          <input
            type="text"
            id="name"
            name="name"
            value={formData.name}
            onChange={handleChange}
          />
        </div>
        <div>
          <label htmlFor="requirements">Requirements</label>
          <textarea
            id="requirements"
            name="requirements"
            value={formData.requirements}
            onChange={handleChange}
          />
        </div>
        <div>
          <label htmlFor="duration_weeks">Duration Weeks</label>
          <input
            type="number"
            id="duration_weeks"
            name="duration_weeks"
            value={formData.duration_weeks}
            onChange={handleChange}
          />
        </div>
        <button type="submit">Create Project</button>
      </form>
    </div>
  );
};

export default NewProjectFields;
