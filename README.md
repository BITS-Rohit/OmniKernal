<div align="center">

<h1>🪐 OmniKernal</h1>

<p><b>Write Code Once. Run It Everywhere.</b></p>

<p>
  <a href="https://github.com/BITS-Rohit/OmniKernal/actions/workflows/ci.yml">
    <img src="https://github.com/BITS-Rohit/OmniKernal/actions/workflows/ci.yml/badge.svg" alt="CI">
  </a>
  <a href="https://github.com/BITS-Rohit/OmniKernal/actions/workflows/pre-commit.yml">
    <img src="https://github.com/BITS-Rohit/OmniKernal/actions/workflows/pre-commit.yml/badge.svg" alt="Pre-commit">
  </a>
  <a href="https://github.com/BITS-Rohit/OmniKernal/blob/main/LICENSE">
    <img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License: MIT">
  </a>
  <img src="https://img.shields.io/badge/python-%3E%3D3.12-3776AB?logo=python&logoColor=white" alt="Python 3.12+">
  <img src="https://img.shields.io/badge/status-Pre--Alpha-orange" alt="Pre-Alpha">
  <img src="https://img.shields.io/badge/type--checked-mypy%20strict-success" alt="mypy strict">
  <img src="https://img.shields.io/badge/linted-ruff-black" alt="ruff">
</p>

</div>

---

**OmniKernal** is a secure, database-driven **microkernel framework** for building scalable, multi-platform automation systems. It provides a modular plugin architecture that cleanly decouples platform-specific code from business logic — enabling isolated, extensible, and fully testable automation workflows.

> OmniKernal is not a bot script. It is infrastructure.

---

## 📑 Table of Contents

- [Why OmniKernal](#-why-omnikernal)
- [Core Architecture](#-core-architecture)
- [Source Layout](#-source-layout)
- [The Execution Flow](#️-the-execution-flow)
- [Contracts & Type Safety](#-contracts--type-safety)
- [Plugin System](#-plugin-system)
- [Database Layer](#️-database-layer)
- [Getting Started](#-getting-started)
- [Running Tests](#-running-tests)
- [Code Quality](#-code-quality)
- [Roadmap & Future Work](#️-roadmap--future-work)
- [Contributing](#-contributing)
- [License](#-license)

---

## 💡 Why OmniKernal

Most automation frameworks couple platform logic tightly with business logic. This creates fragile systems that break when platforms change their APIs, and forces developers to rewrite handlers for every new platform.

OmniKernal solves this by acting as a **kernel** — an intermediary layer that:

| Problem | OmniKernal Solution |
|---|---|
| Platform-specific handler code | `PlatformAdapter` abstraction — adapters are swappable |
| Fragile monolithic command routing | Database-backed routing cache with in-memory hot path |
| No permission enforcement | Role-based access (USER / MODERATOR / ADMIN) per command |
| Unsafe raw user input | `CommandSanitizer` layer strips injections before routing |
| Re-parsing the same message everywhere | Single `IntentPacket` mutated through the full pipeline |
| Plugin discovery is hard-coded | YAML manifest + DB registry — no code changes to add plugins |

---

## 🧠 Core Architecture

OmniKernal is built on three ownership phases, each a self-contained domain:

```
omnikernal/
├── plugin/          ← Phase 1: Plugin lifecycle (load → validate → register)
├── packet/          ← Phase 2: Message pipeline (sanitize → map → execute → reply)
└── database/        ← Phase 3: Persistent state (plugins, commands, roles, logs)
```

Each phase has its own `contracts/`, `interfaces/`, `layers/`, and `adapters/` — no cross-phase leakage.

### IntentPacket — The Pipeline Object

Every inbound message becomes a single mutable `IntentPacket` that travels the entire pipeline. Layers read and write its fields. No data is re-parsed or re-fetched mid-flight.

```python
@dataclass(slots=True)
class IntentPacket:
    message: Message           # Immutable inbound data
    state: PacketState         # RECEIVED → ROUTED → EXECUTING → DONE / FAILED / DROPPED
    sanitized_text: str | None
    required_role: ROLE | None
    mapped_handler: str | None
    args: dict[str, str]       # Parsed CLI-style arguments
    flags: dict[str, Any]      # Dynamic per-message metadata
    result: CommandResult | None
```

Handler API (what plugin developers use):

```python
async def my_handler(ctx: IntentPacket) -> None:
    ctx.resolve("Hello World!")      # success — sets result + transitions to DONE
    ctx.fail("reason")               # failure — sets error_reason + FAILED
    ctx.set_flag("key", value)       # attach arbitrary per-request metadata
```

---

## 📁 Source Layout

```
OmniKernal/
├── src/                          # Package root (maps to `omnikernal` on install)
│   ├── packet/
│   │   ├── contracts/            # IntentPacket, Message, User, CommandResult, RouteCache
│   │   ├── interfaces/           # BaseLayer (pipeline step ABC)
│   │   └── layers/               # Sanitizer → Mapper → Parser → Execution → Response
│   ├── plugin/
│   │   ├── contracts/            # PluginManifest
│   │   ├── interfaces/           # PlatformAdapter, BasePlugin (ABCs)
│   │   ├── adapters/             # AdapterManager, MockAdapter
│   │   └── layers/               # PluginEngine (discover, validate, register)
│   ├── database/
│   │   ├── models.py             # SQLAlchemy ORM models
│   │   ├── repository.py         # OmniRepository — all DB operations
│   │   └── session.py            # Async session factory
│   ├── dashboard/                # (Future) Web dashboard module
│   └── omni_logger.py            # OmniLogger — structured LoggerAdapter
├── tests/
│   ├── adapters/                 # AdapterManager unit tests
│   ├── test_contracts/           # Message, User, CommandResult unit tests
│   ├── test_interfaces/          # BasePlugin, PlatformAdapter ABC tests
│   ├── test_database/            # OmniRepository async integration tests
│   └── smoke/                    # Live CamouChat adapter smoke tests
├── pyproject.toml
└── uv.lock
```

---

## ⚙️ The Execution Flow

```
Platform (WhatsApp / Telegram / Custom)
    │
    ▼
PlatformAdapter.poll_messages()
    │  raw socket / webhook data
    ▼
Message (immutable dataclass — id, raw_text, user, platform, timestamp)
    │
    ▼
GlobalBroker.push()  →  asyncio.Queue[IntentPacket]
    │
    ▼  consumer loop
┌─────────────────────────────────────────┐
│           Inspection Pipeline           │
│                                         │
│  1. CommandSanitizer                    │
│     Strip shell metacharacters,         │
│     newline injection, template tokens  │
│                                         │
│  2. MappingLayer + PermissionValidator  │
│     Resolve command from routing cache  │
│     Check user ROLE against required    │
│                                         │
│  3. Parser                              │
│     Extract --flag style CLI args       │
│                                         │
│  4. ExecutionLayer                      │
│     Dynamically import & call handler  │
│                                         │
│  5. ResponseLayer                       │
│     Route result back to adapter        │
└─────────────────────────────────────────┘
    │
    ▼
PlatformAdapter.send_message(packet)
```

> **Short-circuit rule:** If `packet.state == DROPPED` at any layer, the pipeline halts immediately. No handler is called. No reply is sent.

---

## 🔒 Contracts & Type Safety

All shared data objects are **frozen dataclasses** — immutable by default:

| Contract | Description |
|---|---|
| `Message` | Inbound platform message. Immutable after construction. |
| `User` | Sender identity with platform, display name, and `ROLE`. |
| `CommandResult` | Handler return value. Built via `.success()` or `.error()` factory methods. |
| `RouteCache` | In-memory command routing entry loaded from DB at startup. |
| `PluginManifest` | Parsed `manifest.json` for each plugin. Validated before DB insertion. |
| `CommandManifest` | Individual command metadata: name, prefix, required role, handler path. |

The entire `src/` tree passes **mypy strict** with zero errors.

---

## 🧩 Plugin System

Plugins are **directories** containing:

```
plugins/
└── my_plugin/
    ├── manifest.json     # Identity, version, min_core_version, author
    ├── commands.yaml     # Command definitions: prefix, role, handler_path
    └── handlers/
        └── my_handler.py
```

`PluginEngine` at startup:

1. Scans `plugins/` for valid `manifest.json` files
2. Validates `min_core_version` compatibility
3. Parses `commands.yaml` and builds `CommandManifest` objects
4. Registers everything in the DB — idempotently (safe to re-run)
5. Builds the in-memory `RouteCache` passed to `GlobalBroker`

Handlers are **pure async functions** — they receive an `IntentPacket`, call `ctx.resolve()` or `ctx.fail()`, and return. They never import platform SDKs.

```python
# plugins/my_plugin/handlers/ping.py
async def handle(ctx) -> None:
    ctx.resolve(reply="Pong! 🏓")
```

---

## 🗄️ Database Layer

OmniKernal uses **SQLAlchemy 2.x async** with support for:

| Backend | Driver | Extra |
|---|---|---|
| SQLite (default) | `aiosqlite` | `pip install omnikernal[database-extras]` |
| PostgreSQL | `asyncpg` | `pip install omnikernal[database-extras]` |
| MySQL | `aiomysql` | `pip install omnikernal[database-extras]` |

Configure via environment variable (read at import time by `session.py`):

```bash
# Default — SQLite file created in project root as src.db
export DATABASE_URL="sqlite+aiosqlite:///src.db"

# PostgreSQL
export DATABASE_URL="postgresql+asyncpg://user:pass@localhost/omnikernal"

# Optional: enable SQLAlchemy query echo for debugging
export SQLALCHEMY_ECHO=1
```

`OmniRepository` exposes all DB operations:

```python
repo.register_plugin(manifest)
repo.register_command(command_manifest)
repo.get_routing_cache()          # → dict[str, RouteCache]
repo.log_execution(packet, duration_ms)
```

---

## 🚀 Getting Started

### Prerequisites

- Python `>=3.12`
- [`uv`](https://github.com/astral-sh/uv) (recommended) or `pip`
- Git

### Install with `uv` (Recommended)

```bash
git clone https://github.com/BITS-Rohit/OmniKernal.git
cd OmniKernal

# Create venv, install all dependencies
uv sync

# Activate
source .venv/bin/activate
```

### Install with `pip`

```bash
git clone https://github.com/BITS-Rohit/OmniKernal.git
cd OmniKernal

python -m venv .venv
source .venv/bin/activate

pip install -e ".[dev]"
```

### Minimal Usage

```python
import asyncio
from omnikernal.packet import GlobalBroker
from omnikernal.plugin.adapters import AdapterManager, MockAdapter
from omnikernal.packet.contracts import RouteCache
from omnikernal.packet.contracts.user import ROLE

async def echo_handler(ctx) -> None:
    ctx.resolve(reply=f"Echo: {ctx.message.raw_text}")

async def main():
    routing_cache = {
        "echo": RouteCache(
            command_name="echo",
            pattern=".*",
            handler_path="my_app.handlers.echo_handler",
            required_role=ROLE.USER,
            plugin_name="my_plugin",
        )
    }

    broker = GlobalBroker(routing_cache=routing_cache)
    manager = AdapterManager()

    adapter = MockAdapter()
    manager.register("console", adapter)
    adapter.inject_message("!echo Hello OmniKernal!")

    broker_task = await broker.start()
    await manager.start_all(broker)
    await asyncio.sleep(0.5)

    await manager.stop_all()
    await broker.stop()
    broker_task.cancel()

asyncio.run(main())
```

---

## 🧪 Running Tests

```bash
# Run full test suite with coverage
uv run pytest

# Run specific test module
uv run pytest tests/test_contracts/

# Run only async DB integration tests
uv run pytest tests/test_database/ -v
```

Current coverage: **51%** — growing with each phase completion.

---

## 🛠 Code Quality

OmniKernal enforces strict quality gates on every commit via pre-commit hooks:

```bash
# Run all quality checks manually
uv run pre-commit run --all-files

# Individual tools
uv run ruff check src/          # Lint
uv run ruff format src/         # Format
uv run --active mypy src        # Type check (strict)
uv run deptry .                 # Unused/missing dependency check
```

All of `src/` passes:
- ✅ **ruff** — zero lint errors
- ✅ **mypy strict** — zero type errors
- ✅ **pytest** — 23 tests passing

---

## 🗺️ Roadmap & Future Work

### ✅ Completed

- [x] `IntentPacket` pipeline (sanitize → map → permissions → parse → execute → respond)
- [x] Plugin discovery via `manifest.json` + `commands.yaml`
- [x] DB-backed plugin/command registry (`OmniRepository`)
- [x] `PlatformAdapter` + `AdapterManager` abstractions
- [x] `MockAdapter` for offline testing
- [x] Role-based permission enforcement (USER / MODERATOR / ADMIN)
- [x] `CommandSanitizer` — injection prevention layer
- [x] Structured `OmniLogger` (LoggerAdapter with `.bind()`)
- [x] Strict mypy + ruff passing on full `src/`

### 🔄 In Progress

- [ ] Multi-command extraction (semicolon-delimited message splitting)
- [ ] `IntentPacket` history / audit log via DB
- [ ] Expanded test coverage for all pipeline layers

### 🔮 Future Work

- [ ] **Dashboard** — Web UI for real-time plugin management, command routing visualization, execution metrics, and per-user analytics. Planned as a standalone `src/dashboard/` module using an async-first web framework.
- [ ] **AI Middleware** — Pluggable AI agent hook at the pipeline level for intent classification before routing
- [ ] **Event Listener Registry** — Generic, modular event subscription system beyond message-only triggers
- [ ] **ApiWatchdog** — Automated external API health monitoring triggered by `CommandResult.error` with `api_url` set
- [ ] **Plugin Hot-Reload** — Live reload of plugin handlers without broker restart
- [ ] **Rate Limiting Layer** — Per-user, per-command throttle enforcement
- [ ] **PyPI Publish** — Stable `omnikernal` release on PyPI once architecture is benchmarked

---

## 🤝 Contributing

OmniKernal follows **Domain-Driven Design (DDD)** — every contribution must respect phase ownership boundaries.

**Key rules:**
- `plugin/` code must not import from `packet/`
- `packet/` layers must not import platform-specific SDKs
- All new contracts must be **frozen dataclasses** with `slots=True`
- All public APIs must be **fully type-annotated** and pass mypy strict

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full setup and workflow guide.

**Good first contributions:**
- Adapter development (Telegram, Discord)
- New pipeline layer implementations
- Test coverage for existing layers
- Database optimization
- Security hardening

---

## 📜 License

MIT — see [LICENSE](LICENSE) for details.

---

<div align="center">
  <sub>Built with precision. Designed for scale. OmniKernal.</sub>
</div>
