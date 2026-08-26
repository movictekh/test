# Central Payments

Provider-neutral payment orchestration for Bomach OS.

Core invariant:

- business domains create `PaymentIntent` records with an immutable accounting snapshot;
- provider adapters create attempts and verify external provider events;
- Central Payments records one immutable `ConfirmedReceipt` per intent;
- Finance automatically accounts for the verified receipt exactly once;
- business domains separately mark receipts applied after deciding what the money means.

Central Payments does not mutate Real Estate property/purchase state and contains no
Monnify-specific implementation. Provider adapters belong under `system.payments.providers`.
