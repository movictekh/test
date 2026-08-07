# UI-3.04 — Specialized Services correction

The Service Operations prototype exposes exactly two navigation entries under
**Specialized Services**:

1. **Real Estate Inventory**
2. **Survey / Engineering / Others**

The second screen is intentionally one reusable operational shell with internal
tabs for:

- Land Surveying
- Engineering
- Courier & Logistics
- Information Technology

Those are not separate sidebar modules.

The earlier `Specialized Service Control` label and
`specialized-service-control` route key were implementation inventions and are
replaced by the prototype wording.

Real Estate Inventory remains a separate screen. Its visibility is now granted
to Service Administrator, Head of Operations, and Service Manager in addition
to the roles that already had `realEstateRead`, preventing the Specialized
Services group from appearing as a single-item section for normal operational
management users.
