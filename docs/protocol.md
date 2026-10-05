# State and transition contract — v0.1

## Independent interfaces

A model adapter implements `generate(context) -> dict` and a string `name`.
The context includes the goal, action (`CLARIFY`), policy, active concept path,
concept evidence, source paragraph, annotation thread, and optional follow-up.
Adapters must return `answer: str` and `prerequisites: list[str]`.
Model output is validated before mutation. Unknown keys, including mastery
claims, are not applied. A model must not mutate the provided context.

The SDK is synchronous. Hosts must serialize writes to the same session. The
reference HTTP server uses a mutation lock and reloads state before each action;
the SQLite store lock alone does not provide optimistic concurrency across
multiple independent processes. Run one server per database.

## Snapshot fields

- `schema_version`: integer, currently 1.
- `id`, `goal`, `title`, `updated_at`.
- `document`: revision number and ordered `{id, text}` blocks.
- `annotations`: stable IDs, anchors, original question, concept ID, open/resolved
  state, timestamp, and ordered user/assistant messages.
- `concepts`: stable IDs, names, statuses, and evidence records.
- `stack`: concept IDs ordered from goal to current branch.
- `prerequisites`: accepted `{concept, requires}` edges, created on first push.
- `policy`: frontier_budget, default 1.
- `events`: timestamped transition log alongside the snapshot.

This is a versioned Python/JSON contract, not yet a standardized JSON Schema or
an event-sourced engine. Events explain mutations but are not sufficient for
full replay. The exported document and learner history can be sensitive.

## Anchors

An anchor stores block ID, document revision, exact selected quote, and a
half-open `[start, end)` Unicode code-point range. The browser translates UTF-16
selection offsets into code points; the server checks the exact source slice.
Selections spanning paragraphs are rejected. v0.1 intentionally has no document
editor, preventing silent anchor drift. An edit-capable client must add revision
checks, orphaned-anchor handling and explicit migration before modifying source.

## Evidence and navigation

- A response changes `unseen` to `exposed`, never to `verified`.
- A learner's own explanation is stored as unverified evidence and changes the
  concept to `self_reported`.
- Resolving an annotation changes only the question, not concept mastery.
- `push` accepts a prerequisite, adds its edge, and remembers a return location.
  Returning does not imply that the prerequisite was mastered.
- Active-stack loops are rejected. General dependency graph inference and
  cycle detection beyond the active path are not implemented.
- The one-proposal frontier limit is enforced. Semantic concept counting in
  answer prose is not enforced. A prompt is guidance, not a runtime guarantee.

## Local HTTP API

GET `/api/bootstrap` returns model mode, session list and the local request token.
GET `/api/session?id=...` returns a snapshot.
POST operations return the updated snapshot:
`/api/create`, `/api/annotate`, `/api/ask`, `/api/resolve`, `/api/push`,
`/api/back`, `/api/understanding`.
Each mutation requires the same-origin `Origin` header and `X-Learning-Token`.
Use the SDK for programmatic work rather than treating this local transport as
a public hosted API. Errors do not include provider response bodies or secrets.
