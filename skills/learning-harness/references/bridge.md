# Host bridge and limits

## Supported browser route

Official references checked 2026-10-05:
- https://learn.chatgpt.com/docs/annotations-extensibility
- https://learn.chatgpt.com/docs/webmcp

Use a secure top-level page (HTTPS or localhost). The documented APIs are
`document.oai.annotation.request(element, options)` and
`document.modelContext.registerTool(definition)`. Feature-detect them; they are
not universally available in ChatGPT web, every model, every workspace, ordinary
browsers, or iframe previews. Check current host capabilities rather than a
hard-coded model list. No readiness polling or API-key setup is necessary.

The user first saves a question, then presses **交给当前 Work 回答**. That second
user gesture calls the annotation request synchronously on the connected note
card, carrying flat session, annotation and revision metadata. The browser opens
an editable annotation; the learner must still send it. `accepted: true` means
only that the browser accepted the request, not that a message was sent. Do not
claim a callback or automatic model response from that return value.

The current conversation then uses these registered page tools:

| Tool | Effect |
|---|---|
| learning_get_state | Read full v2 state and revision |
| learning_add_answer | Add the current agent's explanation to an existing note |
| learning_append_content | Append short paragraphs without changing old anchors |
| learning_enter_prerequisite | Push a learner-approved detour |
| learning_return | Pop the return path without claiming mastery |

Writes require `expected_revision` and a unique `operation_id`; stale versions
are rejected and repeated operation IDs do not duplicate the write. Tool results
include the full state for checkpointing. The page validates all transitions and
renders content as text, not HTML. It never calls a model endpoint.

## Storage and portability

The new workspace uses `schema_version: 2`, independent of the legacy SDK's v1
SQLite session format. There is no automatic v1 migration yet. Browser state is
saved under a session-specific localStorage key and survives reload in the same
origin/profile. It is not cross-device sync and can disappear if browser data is
cleared. The agent must preserve returned JSON using the host's durable file
mechanism. The learner can also export it. Rebuild from that snapshot to restore
it elsewhere; don't edit the private snapshot in the public source repo.

## Fallback route

Without annotation support (or if a request is rejected), show a modal with an
explicitly UNSENT question packet to copy into the current conversation. Without
WebMCP, return an explanation plus this packet for manual write-back:

```json
{
  "session_id": "actual-session-id",
  "expected_revision": 3,
  "operation_id": "unique-operation-id",
  "annotation_id": "actual-annotation-id",
  "text": "Explanation written by the current conversation."
}
```

Never ask for a separate API key to work around an unavailable host bridge. No
click in a regular browser silently awakens a Work conversation. Do not advertise
this fallback as automatic or background tutoring. A skill supplies instructions;
it cannot grant missing platform capabilities.
