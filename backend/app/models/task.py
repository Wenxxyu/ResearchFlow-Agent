from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    task_type: Mapped[str] = mapped_column(String(64), index=True)
    user_input: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    final_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    project = relationship("Project", back_populates="tasks")
    steps = relationship("TaskStep", back_populates="task", cascade="all, delete-orphan")
    memories = relationship("Memory", back_populates="source_task")
    created_skills = relationship("Skill", back_populates="created_from_task")
    skill_candidates = relationship("SkillCandidate", back_populates="source_task", cascade="all, delete-orphan")
