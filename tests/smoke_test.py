"""
OmniKernal — Smoke Test

Demonstrates the full Core Engine loop using a directly-registered adapter:
1. Registers MockAdapter with AdapterManager
2. Boots the GlobalBroker with the loaded adapter
3. Injects a simulated message
4. Runs the pipeline: Mapping -> Sanitize -> Parse -> Execute -> Reply
"""

import asyncio

from omnikernal.adapters.manager import AdapterManager
from omnikernal.adapters.mock_adapter import MockAdapter
from omnikernal.core import GlobalBroker
from omnikernal.core.contracts import RouteCache
from omnikernal.core.contracts.user import ROLE


async def echo_handler(packet) -> str:
    """Simple echo command handler executed by ExecutionLayer."""
    return f"Echo response: {packet.message.raw_text}"


async def run_smoke_test():
    # 1. Setup in-memory command routing cache
    print("[SmokeTest] Setting up routing cache...")
    routing_cache = {
        "echo": RouteCache(
            command_name="echo",
            pattern=".*",
            handler_path="tests.smoke_test.echo_handler",
            required_role=ROLE.ADMIN,
            plugin_name="smoke_plugin",
        )
    }

    # 2. Initialize the GlobalBroker and AdapterManager
    print("[SmokeTest] Initializing GlobalBroker...")
    broker = GlobalBroker(routing_cache=routing_cache)
    manager = AdapterManager()

    # 3. Register and inject message into MockAdapter
    print("[SmokeTest] Initializing MockAdapter...")
    adapter = MockAdapter()
    manager.register("console", adapter)

    adapter.inject_message("!echo Smoke Test is Working!")

    # 4. Boot broker and start all adapters
    print("[SmokeTest] Starting Core Broker...")
    broker_task = await broker.start()

    print("[SmokeTest] Starting Adapter Polling...")
    await manager.start_all(broker)

    # Wait briefly for packet execution
    await asyncio.sleep(0.5)

    # 5. Stop all and clean up
    print("[SmokeTest] Stopping Core and Adapters...")
    await manager.stop_all()
    await broker.stop()
    broker_task.cancel()

    # 6. Verify result
    if adapter.sent_messages:
        print(f"\n[PASS] SMOKE TEST PASSED: Received reply -> '{adapter.sent_messages[0]}'")
    else:
        print("\n[FAIL] SMOKE TEST FAILED: No reply generated.")
        raise RuntimeError("Smoke test failed: No output generated.")


if __name__ == "__main__":
    asyncio.run(run_smoke_test())
