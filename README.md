<div align="center">
  <h1>🪐 OmniKernal</h1>
  <p><b>Write Code Once. Run It Everywhere.</b></p>
</div>

**OmniKernel** is a secure, database-driven microkernel framework for building scalable, multi-platform automation systems.
It provides a modular plugin architecture that decouples platform logic from execution logic, enabling extensible and isolated automation workflows.

---

## 🚀 The Universal Messaging Core

OmniKernel is not a bot script.
It is a foundation for building automation ecosystems.

Our core philosophy is simple: **Write Code Once, Run It Everywhere.** 
Whether you are deploying to WhatsApp, Telegram, Discord, or a custom internal API, your plugin logic never changes. OmniKernal handles the platform complexities, protocol translations, and state management completely invisibly.

---

## 🧠 Core Architecture

OmniKernal abandons fragile, monolithic routing in favor of a **Domain-Driven, Pipeline-Based Architecture**.

### 1. 📦 IntentPacket Pipeline
Every incoming message is encapsulated into a mutable `IntentPacket`. This single state object flows through the entire system — from Sanitization to Permissions, Mapping, Execution, and Response. Middlewares and AI agents mutate this state seamlessly without redundant data parsing.

Command format example:
```
<command_name> <arguments>
```

Example:
```
!ytaudio <youtube_url>
!stats <username>
```

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

OmniKernel is under active development.
Architecture is being stabilized prior to benchmarking and research validation.

---

## 📜 License

MIT

---

## 🤝 Contributing

We welcome contributions focused on:
- Adapter development
- Plugin system improvements
- Database optimization
- Security hardening
- Performance benchmarking

---

OmniKernel is not just automation.
It is infrastructure.
