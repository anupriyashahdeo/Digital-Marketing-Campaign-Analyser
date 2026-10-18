from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# STEP 3+: add these back to the imports when you uncomment the tables below
# from datetime import date
# from sqlalchemy import Date, Text
# from sqlalchemy.orm import relationship


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# STEP 1 (active): users table for login.
# ---------------------------------------------------------------------------
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# ---------------------------------------------------------------------------
# STEP 2 (active): workspaces + runs. Every user gets a personal workspace at
# signup; all data belongs to a workspace (not a user) so teams can share later.
# ---------------------------------------------------------------------------
ROLES = ("owner", "editor", "viewer")
RUN_STATUSES = ("queued", "running", "completed", "failed", "cancelled")


class Workspace(Base):
    __tablename__ = "workspaces"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    region: Mapped[str] = mapped_column(String(2), default="IN")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("user_id", "workspace_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"),
                                              index=True)
    role: Mapped[str] = mapped_column(String(10), default="owner")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Run(Base):
    __tablename__ = "runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"),
                                              index=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"),
                                                   nullable=True)
    category: Mapped[str] = mapped_column(String(200))
    keywords: Mapped[list] = mapped_column(JSON, default=list)
    region: Mapped[str] = mapped_column(String(2), default="IN")
    language: Mapped[str] = mapped_column(String(8), default="en")
    status: Mapped[str] = mapped_column(String(20), default="queued", index=True)
    ad_count: Mapped[int] = mapped_column(Integer, default=0)
    spent_usd: Mapped[float] = mapped_column(Float, default=0)
    error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


# ---------------------------------------------------------------------------
# STEP 3+: ads, answers, scores, cost ledger.
# Uncomment when you build that step (see docs/ROADMAP.md).
# When Ad is switched on, add to Run:  ads: Mapped[list["Ad"]] = relationship(back_populates="run")
# ---------------------------------------------------------------------------
#
# class Ad(Base):
#     __tablename__ = "ads"
#     id: Mapped[int] = mapped_column(primary_key=True)
#     run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), index=True)
#     video_id: Mapped[str] = mapped_column(String(20), index=True)
#     advertiser: Mapped[str] = mapped_column(String(200), default="")
#     region: Mapped[str] = mapped_column(String(2), default="IN")
#     language: Mapped[str] = mapped_column(String(8), default="en")
#     first_shown: Mapped[date | None] = mapped_column(Date, nullable=True)
#     last_shown: Mapped[date | None] = mapped_column(Date, nullable=True)
#     variants: Mapped[int] = mapped_column(Integer, default=1)
#     evidence_level: Mapped[str] = mapped_column(String(24), default="organic_only")
#     raw: Mapped[dict] = mapped_column(JSON, default=dict)
#     run: Mapped[Run] = relationship(back_populates="ads")
#
#
# class AdText(Base):
#     __tablename__ = "ad_texts"
#     id: Mapped[int] = mapped_column(primary_key=True)
#     ad_id: Mapped[int] = mapped_column(ForeignKey("ads.id"), unique=True)
#     text: Mapped[str] = mapped_column(Text)
#
#
# class AnswerRow(Base):
#     __tablename__ = "answers"
#     id: Mapped[int] = mapped_column(primary_key=True)
#     ad_id: Mapped[int] = mapped_column(ForeignKey("ads.id"), index=True)
#     question_id: Mapped[str] = mapped_column(String(50))
#     question_version: Mapped[str] = mapped_column(String(10))
#     value: Mapped[dict] = mapped_column(JSON)
#     confidence: Mapped[float] = mapped_column(Float)
#     evidence: Mapped[str] = mapped_column(Text, default="")
#     answered_by: Mapped[str] = mapped_column(String(30))
#
#
# class ScoreRow(Base):
#     __tablename__ = "scores"
#     id: Mapped[int] = mapped_column(primary_key=True)
#     ad_id: Mapped[int] = mapped_column(ForeignKey("ads.id"), unique=True)
#     label: Mapped[str] = mapped_column(String(12))
#     confidence: Mapped[str] = mapped_column(String(10))
#     engagement_z: Mapped[float | None] = mapped_column(Float, nullable=True)
#     run_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
#     reasons: Mapped[list] = mapped_column(JSON, default=list)
#
#
# class CostEntry(Base):
#     __tablename__ = "cost_ledger"
#     id: Mapped[int] = mapped_column(primary_key=True)
#     run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), index=True)
#     provider: Mapped[str] = mapped_column(String(30))
#     usd: Mapped[float] = mapped_column(Float)