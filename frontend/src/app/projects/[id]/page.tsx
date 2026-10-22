"use client";
import { useParams } from "next/navigation";
import { useProjectStore } from "@/store/projectStore";
import { useEffect, useState } from "react";
import { projectApi } from "@/lib/project";
import { TeamMember } from "@/types/teamMember";
import { Sprint } from "@/types/sprint";
import { teamMemberApi } from "@/lib/teamMember";
import { sprintApi } from "@/lib/sprint";
import { taskApi } from "@/lib/task";
import { Task, TaskStatus } from "@/types/task";
import { useAuthStore } from "@/store/authStore";

const ProjectByIDPage = () => {
  const { currentProject, loadProject, isLoading, error } = useProjectStore();
  const { id } = useParams<{ id: string }>();

  const { user } = useAuthStore();
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [teamMembers, setTeamMembers] = useState<TeamMember[]>([]);
  const [sprints, setSprints] = useState<Sprint[]>([]);
  const [newMemberUserId, setNewMemberUserId] = useState("");
  const [newMemberSkills, setNewMemberSkills] = useState("");
  const [sprintStartDate, setSprintStartDate] = useState("");
  const [tasks, setTasks] = useState<Task[]>([]);

  useEffect(() => {
    const loadData = async () => {
      await loadProject(id as string);
      const members = await teamMemberApi.list(id as string);
      setTeamMembers(members);
      const sprintList = await sprintApi.list(id as string);
      setSprints(sprintList);
      const taskList = await taskApi.list(id as string);
      setTasks(taskList);
    };
    loadData();
  }, [id, loadProject]);

  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;

  const backlog = tasks.filter((task) => task.status === TaskStatus.BACKLOG);
  const boardTasks = tasks.filter(
    (task) => task.sprint_id !== null && task.status !== TaskStatus.BACKLOG,
  );

  const moveTask = async (taskId: string, status: TaskStatus) => {
    try {
      setActionError(null);
      const updated = await taskApi.update(taskId, { status });
      setTasks(
        (current) =>
          current.map((task) =>
            task.id === taskId ? updated : task,
          ) as Task[],
      );
    } catch (err: unknown) {
      setActionError(
        err instanceof Error ? err.message : "Failed to update task status",
      );
    }
  };

  return (
    <div>
      <div>
        {user?.id === currentProject?.created_by_id && (
          <div>
            <p>You are the owner of this project your user id is {user?.id}</p>
          </div>
        )}
        <h1>{currentProject?.name}</h1>
        <p>{currentProject?.status}</p>
        <p>{currentProject?.duration_weeks} weeks</p>
        <p>{currentProject?.requirements}</p>
        {currentProject?.ai_opinion && <p>{currentProject?.ai_opinion}</p>}
        <p>{currentProject?.created_at}</p>
        <p>{currentProject?.updated_at}</p>
      </div>
      <div>
        {actionMessage && <p style={{ color: "green" }}>{actionMessage}</p>}
        {actionError && <p style={{ color: "red" }}>{actionError}</p>}
        <span>
          <button
            onClick={async () => {
              try {
                setActionError(null);
                await projectApi.runAnalysis(id as string);
                await loadProject(id as string);
                const taskList = await taskApi.list(id as string);
                setTasks(taskList);
                setActionMessage("Analysis completed successfully");
              } catch (err: unknown) {
                setActionError(
                  err instanceof Error
                    ? err.message
                    : "Failed to run analysis due to unknown error",
                );
              }
            }}
          >
            Run Analysis
          </button>
          <button
            onClick={async () => {
              try {
                setActionError(null);
                await projectApi.planSprint(id as string);
                setActionMessage("Sprint planned successfully");
              } catch (err: unknown) {
                setActionError(
                  err instanceof Error
                    ? err.message
                    : "Failed to plan sprint due to unknown error",
                );
              }
            }}
          >
            Plan Sprint
          </button>
          <button
            onClick={async () => {
              try {
                setActionError(null);
                await projectApi.analyzeRisks(id as string);
                const taskList = await taskApi.list(id as string);
                setTasks(taskList);
                setActionMessage("Risks analyzed successfully");
              } catch (err: unknown) {
                setActionError(
                  err instanceof Error
                    ? err.message
                    : "Failed to analyze risks due to unknown error",
                );
              }
            }}
          >
            Analyze Risks
          </button>
          <button
            onClick={async () => {
              try {
                setActionError(null);
                await projectApi.createSprints(id as string);
                setActionMessage("Sprints created successfully");
              } catch (err: unknown) {
                setActionError(
                  err instanceof Error
                    ? err.message
                    : "Failed to create sprints due to unknown error",
                );
              }
            }}
          >
            Create Sprints
          </button>
        </span>
      </div>

      <div>
        <h2>Team Members</h2>
        <ul>
          {teamMembers.map((member) => (
            <li key={member.id}>
              {member.name} - Skills: {member.skills.join(", ")}
            </li>
          ))}
        </ul>

        <h3>Add Team Member</h3>
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            try {
              const newMember = await teamMemberApi.create({
                user_id: newMemberUserId,
                project_id: id as string,
                skills: newMemberSkills.split(",").map((s) => s.trim()),
              });
              setTeamMembers([...teamMembers, newMember]);
              setNewMemberUserId("");
              setNewMemberSkills("");
              setActionMessage("Team member added successfully!");
            } catch (err) {
              setActionError(
                err instanceof Error ? err.message : "Failed to add member",
              );
            }
          }}
        >
          <input
            type="text"
            placeholder="User ID"
            value={newMemberUserId}
            onChange={(e) => setNewMemberUserId(e.target.value)}
            required
          />
          <input
            type="text"
            placeholder="Skills (comma-separated)"
            value={newMemberSkills}
            onChange={(e) => setNewMemberSkills(e.target.value)}
          />
          <button type="submit">Add Member</button>
        </form>
      </div>

      <div>
        <h2>Sprints</h2>
        <ul>
          {sprints.map((sprint) => (
            <li key={sprint.id}>
              Sprint {sprint.index}: {sprint.start_date} to {sprint.end_date}
            </li>
          ))}
        </ul>

        <h3>Create Sprints</h3>
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            try {
              const newSprints = await sprintApi.create({
                project_id: id as string,
                start_date: sprintStartDate,
              });
              setSprints(newSprints);
              setSprintStartDate("");
              setActionMessage("Sprints created successfully!");
            } catch (err) {
              setActionError(
                err instanceof Error ? err.message : "Failed to create sprints",
              );
            }
          }}
        >
          <input
            type="date"
            value={sprintStartDate}
            onChange={(e) => setSprintStartDate(e.target.value)}
            required
          />
          <button type="submit">Create Sprints</button>
        </form>
      </div>
      <div>
        <h2>Backlog</h2>
        <ul>
          {backlog.map((task) => (
            <li key={task.id}>
              {task.title} = Story Points: {task.story_points || "N/A"}
              {task.assignee_id &&
                ` - Assignee: ${teamMembers.find((member) => member.id === task.assignee_id)?.name ?? "Unknown"}`}
              {task.risk_flag && <span style={{ color: "red" }}>AT RISK</span>}
            </li>
          ))}
        </ul>
        <h2>Sprint Board</h2>
        {[TaskStatus.TODO, TaskStatus.DOING, TaskStatus.DONE].map((column) => (
          <div key={column}>
            <h3>{column}</h3>
            <ul>
              {boardTasks
                .filter((task) => task.status === column)
                .map((task) => (
                  <li key={task.id}>
                    {task.title} - Story Points: {task.story_points || "N/A"}
                    {task.assignee_id &&
                      ` - Assignee: ${teamMembers.find((member) => member.id === task.assignee_id)?.name ?? "Unknown"}`}
                    {task.risk_flag && (
                      <span style={{ color: "red" }}>AT RISK</span>
                    )}
                    {[TaskStatus.TODO, TaskStatus.DOING, TaskStatus.DONE]
                      .filter((status) => status !== task.status)
                      .map((status) => (
                        <button
                          key={status}
                          type="button"
                          onClick={() => moveTask(task.id, status)}
                        >
                          Move to {status}
                        </button>
                      ))}
                  </li>
                ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ProjectByIDPage;
