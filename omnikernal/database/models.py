"""
Database Models, SQLAlchemy Declarative Schema

Defines the tables for the Microkernel plugin/tool registry and execution audit log.
Note: RoutingRule (regex-based routing) was removed — routing now uses O(1) cache.
"""

from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Plugin(Base):
    """
    Registry for installed/discovered plugins.
    Primary source: manifest.json
    """

    __tablename__ = "plugins"

    name: Mapped[str] = mapped_column(String(50), primary_key=True)
    version: Mapped[str] = mapped_column(String(20))
    author: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    tools: Mapped[list["Tool"]] = relationship(
        back_populates="plugin", cascade="all, delete-orphan"
    )


class Tool(Base):
    """
    Registry for individual command handlers.
    Primary source: commands.yaml
    """

    __tablename__ = "tools"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    command_name: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    pattern: Mapped[str] = mapped_column(String(255))
    handler_path: Mapped[str] = mapped_column(String(255))  # e.g. "plugins.echo.handlers.echo"
    plugin_name: Mapped[str] = mapped_column(ForeignKey("plugins.name", ondelete="CASCADE"))
    required_role: Mapped[str] = mapped_column(String(20), default="user")

    # Metadata
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    requires_api_key: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    plugin: Mapped["Plugin"] = relationship(back_populates="tools")


class ExecutionLog(Base):
    """
    Audit trail for every command execution.
    """

    __tablename__ = "execution_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), index=True
    )
    user_id: Mapped[str] = mapped_column(String(100))
    platform: Mapped[str] = mapped_column(String(50))
    command_name: Mapped[str] = mapped_column(String(50))
    raw_input: Mapped[str] = mapped_column(Text)
    success: Mapped[bool] = mapped_column(Boolean)
    response_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_reason: Mapped[str | None] = mapped_column(Text, nullable=True)



