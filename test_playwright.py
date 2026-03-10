"""
OmniKernal — WhatsApp Playwright Integration Test Runner

Boots OmniKernal with the WhatsAppPlaywrightAdapter.
Opens a headed Chromium browser so you can scan the QR code manually.
Once logged in, the Core polls for new messages and routes any commands.

Test: send "!sys_plugins" from any WhatsApp chat to yourself.
Expected reply: list of all registered plugins.

Usage:
    uv run python test_playwright.py
"""

import asyncio
import os
import sys

# Ensure src and plugins are in path
sys.path.insert(0, os.path.abspath("."))

from src.core.engine import OmniKernal
from src.database.session import async_session_factory, init_db
from src.database.repository import OmniRepository
from adapter_packs.whatsapp_playwright.adapter import WhatsAppPlaywrightAdapter


async def main() -> None:
    print("🚀 Booting OmniKernal with WhatsApp Playwright Adapter...")

    # Initialize DB schema
    await init_db()

    adapter = WhatsAppPlaywrightAdapter()

    async with async_session_factory() as session:
        repo = OmniRepository(session)
        core = OmniKernal(
            adapter=adapter,
            repository=repo,
            session_factory=async_session_factory,
            profile_name="whatsapp_test",
            mode="self",
        )

        try:
            await core.start()
        except KeyboardInterrupt:
            # core.start() blocks on _stop_event; Ctrl+C raises here
            pass
        finally:
            # Ensure graceful shutdown even if start() raised
            if core.is_running:
                await core.stop()
            print("\n✅ OmniKernal stopped cleanly.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
