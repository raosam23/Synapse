"""SQLModel schema for task dependencies."""

from uuid import UUID, uuid4

from sqlmodel import CheckConstraint, Field, SQLModel, UniqueConstraint


class TaskDependency(SQLModel, table=True):
    """Edge meaning: from_task must precede / finish before to_task can start."""

    __tablename__ = "task_dependencies"
    __table_args__ = (
        UniqueConstraint("from_task_id", "to_task_id", name="uq_task_dependency_edge"),
        CheckConstraint(
            "from_task_id <> to_task_id",
            name="ck_task_dependency_no_self_reference",
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    from_task_id: UUID = Field(foreign_key="tasks.id")
    to_task_id: UUID = Field(foreign_key="tasks.id")
