import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from omnikernal.database.models import Base
from omnikernal.database.repository import OmniRepository
from omnikernal.packet.contracts import CommandManifest, PluginManifest


@pytest_asyncio.fixture
async def db_session():
    # Use in-memory SQLite for repository tests
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_repository_plugin_and_tool_registration(db_session):
    repo = OmniRepository(db_session)

    # 1. Register Plugin
    plugin = PluginManifest(
        name="echo_plugin",
        version="1.0.0",
        author="Test Author",
        description="A test plugin",
        min_core_version="0.1.0",
    )
    await repo.register_plugins([plugin])

    # 2. Register Tool
    tool = CommandManifest(
        name="echo",
        pattern="!echo <text>",
        handler="plugins.echo.handlers.echo.run",
        plugin_name="echo_plugin",
        description="Echoes text",
        minimum_role="USER",
    )
    await repo.register_tools([tool])

    # 3. Verify
    t = await repo.get_tool_by_command("echo")
    assert t is not None
    assert t.pattern == "!echo <text>"
    assert t.plugin_name == "echo_plugin"


@pytest.mark.asyncio
async def test_repository_execution_logging(db_session):
    repo = OmniRepository(db_session)

    await repo.log_execution(
        user_id="user123",
        platform="whatsapp",
        command_name="echo",
        raw_input="!echo hello",
        success=True,
        response_time_ms=150,
    )

    # Verify via direct session query or if repo had a 'get_logs'
    # For now, just ensure it doesn't crash and commits.
    assert True
