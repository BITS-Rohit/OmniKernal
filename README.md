<div align="center">
  <h1>🪐 OmniKernal</h1>
  <p><b>Write Code Once. Run It Everywhere.</b></p>
</div>

<p align="center">
  <img src="https://img.shields.io/badge/Architecture-Domain_Driven-brightgreen" alt="Architecture" />
  <img src="https://img.shields.io/badge/State-Intent_Packet_Pipeline-blue" alt="Pipeline" />
  <img src="https://img.shields.io/badge/Platform-Agnostic-yellow" alt="Agnostic" />
</p>

---

## 🚀 The Universal Messaging Core

OmniKernal is an advanced, strictly decoupled execution engine designed for cross-platform chat automation. 

Our core philosophy is simple: **Write Code Once, Run It Everywhere.** 
Whether you are deploying to WhatsApp, Telegram, Discord, or a custom internal API, your plugin logic never changes. OmniKernal handles the platform complexities, protocol translations, and state management completely invisibly.

---

## 🧠 Core Architecture

OmniKernal abandons fragile, monolithic routing in favor of a **Domain-Driven, Pipeline-Based Architecture**.

### 1. 📦 IntentPacket Pipeline
Every incoming message is encapsulated into a mutable `IntentPacket`. This single state object flows through the entire system — from Sanitization to Permissions, Mapping, Execution, and Response. Middlewares and AI agents mutate this state seamlessly without redundant data parsing.

### 2. 🔌 Platform Adapters
Adapters act as the bridge between raw platform APIs (like Baileys or WAHA) and the Core. They normalize incoming data into the strict OmniKernal `Message` contract and dispatch `IntentPacket` replies back to the target platform perfectly.

### 3. 🧩 Plugin Ecosystem & DB Registry
Plugins are packaged by business feature. OmniKernal uses a robust, database-backed registry to track plugin states, command schemas, and runtime execution metrics dynamically.
- **Dynamic Configurations:** Admins can disable plugins or modify permission roles at runtime instantly.
- **Agnostic Handlers:** Handlers simply receive arguments and a safe context. They never touch platform-specific SDKs.

---

## ⚙️ The Execution Flow

1. **Adapter Ingestion:** Platform-specific adapter receives raw socket/webhook data.
2. **Normalization:** Data maps securely to a strict `Message` dataclass.
3. **Global Broker:** The `Message` enters the `IntentPacket` pipeline.
4. **Inspection Layers:** 
   - *Sanitizer:* Strips dangerous characters completely.
   - *Mapper:* Resolves dynamic command prefixes via optimized routing cache.
   - *Permission:* Validates user roles against persistent database rules.
5. **Execution Layer:** Dynamically loads and runs the specific plugin handler safely.
6. **Response Layer:** Routes the executed output back to the originating Adapter precisely.

---

## 👩‍💻 Contributing

OmniKernal operates on a strict **Domain-Driven Design (DDD)** structure. 
Contributors must ensure all new components respect the Single Responsibility Principle and maintain strict isolation from platform-specific code. 

Please read the contribution guidelines before opening pull requests.

---
<p align="center">Built for scalability. Engineered for perfection.</p>