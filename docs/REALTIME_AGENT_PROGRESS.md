# Real-time agent progress

The progress bus is transport-neutral. It preserves agent events and exposes an
async subscription stream that can be adapted to SSE or WebSockets by the web
layer. Events are structured and include a timestamp and payload.

The dashboard provides repository explorer, code viewer, timeline, investigation,
root-cause, diff, test, Git, and audit panels. It does not change orchestration
business logic.

Recommended production transport: authenticated SSE for one-way progress from
server to browser; WebSockets can be used where bidirectional control is needed.
