"""
OmniKernal — Smoke Test

Demonstrates the full Core Engine loop using a directly-registered adapter:
1. Registers ConsoleMockAdapter with AdapterLoader
2. Boots the engine with the loaded adapter
3. Injects a simulated message
4. Runs the pipeline: Sanitize -> Parse -> Route -> Execute -> Reply
"""

import asyncio

from omnikernal.adapters.console_mock import ConsoleMockAdapter
from omnikernal.adapters.loader import AdapterLoader
from omnikernal.core.engine import OmniKernal
from omnikernal.database.repository import OmniRepository
from omnikernal.database.session import (
    async_session_factory,
    ensure_db_initialized,
)


async def run_smoke_test():
    # 1. Initialize DB and Repository
    print("[Core] Initializing Database...")
    await ensure_db_initialized()

    async with async_session_factory() as session:
        repo = OmniRepository(session)

        # 2. Register and load adapter
        print("[Core] Loading adapter: console...")
        loader = AdapterLoader()
        loader.register("console", ConsoleMockAdapter)
        adapter = loader.load("console")

        # 3. Inject a test message
        adapter.inject_message("!echo Smoke Test is Working!")

        # 4. Boot the engine
        engine = OmniKernal(adapter, repo)

        print("[Core] Starting Engine...")
        engine_task = asyncio.create_task(engine.start())

        # Wait for message processing
        await asyncio.sleep(2)

        print("[Core] Stopping Engine...")
        await engine.stop()
        await engine_task

        if adapter.sent_messages:
            print("\n[PASS] SMOKE TEST PASSED: Adapter + Engine pipeline working!")
        else:
            print("\n[FAIL] SMOKE TEST FAILED: No reply generated.")


if __name__ == "__main__":
    asyncio.run(run_smoke_test())
