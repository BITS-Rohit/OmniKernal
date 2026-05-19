"""
bench_router.py — Routing Latency Benchmark

Simulates 500 plugins × 10 commands each (5000 tools total).
Uses in-memory SQLite (aiosqlite) — no disk I/O noise.

Measures p50/p95/p99/max latency of get_route() for:
  - BEFORE FIX : per-message DB SELECT (old arch)
  - AFTER FIX  : in-memory tool_cache dict, O(1)
  - BASELINE   : pure Python dict (theoretical floor)

Run:
    uv run python tests/bench_router.py
"""

import asyncio
import random
import statistics
import time

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from omnikernal.database.models import Base
from omnikernal.database.repository import OmniRepository
from omnikernal.security.router import CommandRouter, RulesCache

NUM_PLUGINS = 500
CMDS_PER_PLUGIN = 10
TOTAL_CMDS = NUM_PLUGINS * CMDS_PER_PLUGIN
BENCH_ROUNDS = 500


async def seed_db(repo: OmniRepository) -> list[str]:
    all_cmds: list[str] = []
    print(f"Seeding {NUM_PLUGINS} plugins × {CMDS_PER_PLUGIN} cmds …", flush=True)
    t0 = time.perf_counter()
    for p in range(NUM_PLUGINS):
        pname = f"plugin_{p:04d}"
        await repo.register_plugin(name=pname, version="0.1.0", author_name="bench")
        for c in range(CMDS_PER_PLUGIN):
            cmd = f"cmd_{p:04d}_{c:02d}"
            await repo.register_tool(
                command_name=cmd,
                pattern=f"!{cmd}",
                handler_path=f"{pname}.handler_{c}",
                plugin_name=pname,
            )
            all_cmds.append(cmd)
    elapsed = time.perf_counter() - t0
    print(f"  Seed done: {TOTAL_CMDS} tools in {elapsed:.2f}s", flush=True)
    return all_cmds


def print_stats(label: str, latencies_ms: list[float]) -> float:
    latencies_ms.sort()
    p50 = statistics.median(latencies_ms)
    p95 = latencies_ms[int(0.95 * len(latencies_ms))]
    p99 = latencies_ms[int(0.99 * len(latencies_ms))]
    pmax = latencies_ms[-1]
    pmin = latencies_ms[0]
    u1 = sum(1 for x in latencies_ms if x < 1.0)
    u01 = sum(1 for x in latencies_ms if x < 0.1)
    print(f"\n── {label} ({BENCH_ROUNDS} lookups, {TOTAL_CMDS} tools) ──")
    print(f"  min    : {pmin:.5f} ms")
    print(f"  p50    : {p50:.5f} ms")
    print(f"  p95    : {p95:.5f} ms")
    print(f"  p99    : {p99:.5f} ms")
    print(f"  max    : {pmax:.5f} ms")
    print(f"  <1ms   : {u1}/{BENCH_ROUNDS} ({100 * u1 / BENCH_ROUNDS:.1f}%)")
    print(f"  <0.1ms : {u01}/{BENCH_ROUNDS} ({100 * u01 / BENCH_ROUNDS:.1f}%)")
    return p50


async def bench(router: CommandRouter, cmds: list[str], label: str) -> float:
    samples = random.choices(cmds, k=BENCH_ROUNDS)
    latencies_ms: list[float] = []
    for cmd in samples:
        t0 = time.perf_counter()
        result = await router.get_route(cmd)
        latencies_ms.append((time.perf_counter() - t0) * 1000)
        assert result is not None, f"Route not found: {cmd}"
    return print_stats(label, latencies_ms)


async def main() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    # ── Seed ──────────────────────────────────────────────────────────────────
    seed_t0 = time.perf_counter()
    async with Session() as session:
        repo = OmniRepository(session)
        all_cmds = await seed_db(repo)
    seed_elapsed = time.perf_counter() - seed_t0

    # ── BEFORE FIX: simulate old per-message DB SELECT ────────────────────────
    # Patch _ensure_tool_cache to always go to DB (never cache)
    class NoCacheRouter(CommandRouter):
        async def _ensure_tool_cache(self):  # type: ignore[override]
            tools = await self.repository.get_all_tools()
            return {
                t.command_name: {
                    "id": t.id,
                    "command_name": t.command_name,
                    "pattern": t.pattern,
                    "handler_path": t.handler_path,
                    "plugin_name": t.plugin_name,
                    "required_role": t.required_role,
                }
                for t in tools
            }

    shared_old = RulesCache()
    async with Session() as session:
        repo = OmniRepository(session)
        router_old = NoCacheRouter(repo, cache=shared_old)
        p50_old = await bench(router_old, all_cmds, "BEFORE FIX (per-message DB SELECT)")

    # ── AFTER FIX: tool_cache bulk-loaded once, O(1) dict lookup ─────────────
    shared_new = RulesCache()
    async with Session() as session:
        repo = OmniRepository(session)
        router_new = CommandRouter(repo, cache=shared_new)
        p50_new = await bench(router_new, all_cmds, "AFTER FIX  (in-memory dict, O(1))")

    # ── BASELINE: pure Python dict (no async, no router) ─────────────────────
    pure_dict = {cmd: {"command_name": cmd} for cmd in all_cmds}
    samples = random.choices(all_cmds, k=BENCH_ROUNDS)
    lat_pure: list[float] = []
    for cmd in samples:
        t0 = time.perf_counter()
        _ = pure_dict.get(cmd)
        lat_pure.append((time.perf_counter() - t0) * 1000)
    p50_pure = print_stats("BASELINE   (pure Python dict, zero async overhead)", lat_pure)

    # ── Final Report ──────────────────────────────────────────────────────────
    speedup = p50_old / p50_new if p50_new > 0 else float("inf")
    print("\n" + "=" * 62)
    print("  TIMING BREAKDOWN REPORT")
    print("=" * 62)
    print(f"  Seed 5000 tools (one-time startup) : {seed_elapsed:.2f}s")
    print(f"  Per-message DB SELECT  [OLD arch]  : p50 ≈ {p50_old:.3f} ms")
    print(f"  In-memory dict lookup  [NEW arch]  : p50 ≈ {p50_new:.5f} ms")
    print(f"  Pure Python dict       [floor]     : p50 ≈ {p50_pure:.6f} ms")
    print(f"  Speedup (old → new)                : {speedup:.0f}×")
    print()
    if p50_new < 1.0:
        print("  ✅  Resume claim '<1ms resolution latency' is NOW VALID.")
    else:
        print("  ❌  Still above 1ms — cache not working correctly.")
    print("=" * 62)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
