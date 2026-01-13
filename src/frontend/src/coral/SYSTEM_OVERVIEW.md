# coral.config

**Coral Config** defines the application’s structural baseline — component scaffolding, prebuilt modules, import bundling, and system-wide utilities.

> This folder is not intended for feature development.

---

## What Lives Here

- `components/` – Stateless layout primitives like `Header`, `PanelLeft`, `PanelRight`, `Content`, etc. These are styled and functional, but intentionally generic.
- `modules/` – Composite UI blocks that encapsulate common layouts and logic (e.g., a full-width `ChatPanel`, or a `PanelLeft` with navigation baked in). These are production-ready and reusable
- `imports/` – Centralized icon and asset imports to streamline DX and reduce boilerplate.
- `eventbus.ts` – Shared event system for cross-component communication.
- `PanelRegistry.ts` – Central config for registering and referencing dynamic panel zones.

---

## When Should You Modify This?

Only when you're:
- Creating or updating shared UI primitives
- Building new reusable modules
- Extending foundational architecture

Avoid editing directly unless your change impacts system-level behavior. When in doubt, route it through the Coral steward or log it in the dev sync.

---

## Design Philosophy

Coral isolates **infrastructure from implementation** — keeping base components clean and predictable, while enabling rapid development through composable modules.

This layer isn’t for experiments. It’s for the architecture that lets experiments happen without breaking production.

---

🐙