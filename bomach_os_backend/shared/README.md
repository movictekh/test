# Shared primitives

`shared` owns only domain-neutral, stateless primitives that can be depended on
by domains and system capabilities without importing business ownership.

It must not become a dumping ground for models, workflows, permissions,
business services, or cross-domain state.

Current canonical primitive:

- `shared.api.schema.MessageSchema` — generic `{detail: str}` API message schema.

Legacy `services.api.schema.others.MessageSchema` remains a compatibility export
during the modular-monolith migration.
