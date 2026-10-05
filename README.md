# Learning Harness

An open-source, local-first learning runtime with an annotatable document client.

**Select → question → clarify → resolve.** Keep confusion attached to the passage
that caused it, preserve a return path when exploring prerequisites, and carry
learning state between sessions and model adapters.

This repository includes a **v0.2 agent-taught workspace** and the original
**v0.1 local app / Python SDK**. Neither is a validated adaptive tutor.


## Let the current agent teach you — new in v0.2

Give this repository to ChatGPT Work or another capable agent and ask it to read
[`skills/learning-harness/SKILL.md`](skills/learning-harness/SKILL.md). The **agent
in your current conversation** writes the lesson and explanations; the generated
workspace does not call an LLM API or require a second model subscription/key.

Example request:

> Read the learning-harness skill in this repository. Use it to teach me looped
> transformers through a short, annotatable learning document. You are the tutor;
> do not ask me to configure a model API. Check which browser bridge is available.

The skill bundles a standalone page renderer, state transitions, and a browser
bridge. It can generate a subject-specific workspace from a small JSON lesson:

```bash
python3 skills/learning-harness/scripts/build_workspace.py \
  --input examples/work-lesson.json --output /tmp/learning-workspace/index.html \
  --state-output /tmp/learning-workspace/state.json
python3 -m http.server 8765 --bind 127.0.0.1 --directory /tmp/learning-workspace
```

These commands are optional developer setup; a capable agent handles generation
and chooses an accessible local or hosted surface for the learner. A cloud task's
localhost is not automatically reachable from your computer.

### What is connected, exactly?

1. Select a passage and save a question in the page.
2. Press **交给当前 Work 回答**. In a supported built-in browser, the page opens
   a browser annotation with the question and session IDs. **You still send that
   annotation in the conversation.** An accepted request is not proof of sending.
3. The current agent reads the live learning state and writes its own explanation
   back using the page's WebMCP tools. No inference request originates from the page.
4. The agent saves the returned JSON as a durable checkpoint using its host's file
   tools. Browser localStorage alone is not cross-device persistence.

| Environment | Question handoff / write-back |
|---|---|
| Supported ChatGPT built-in browser with annotations + site tools | Browser annotation into the conversation; agent writes back through WebMCP |
| Only browser annotations available | Annotation into the conversation; manual answer packet if no writable page tools |
| Regular browser, iframe preview, or unsupported host | Copy the question packet to the conversation, then paste the answer packet back |

This is not a universal automatic bridge for every ChatGPT web session. The page
feature-detects the official APIs and shows the mode actually available. If a
skill is installed, invoke it by name; providing a GitHub URL alone does not
install it or grant browser capabilities. The UI preserves manual operation when
the host APIs are absent or a request is rejected.

The v0.2 workspace uses a separate versioned JSON schema. It supports stable
anchors, explicit resolution, learner evidence, prerequisite return paths,
append-only teaching content, duplicate-write protection, and stale-write
rejection. Existing v0.1 SQLite sessions are **not automatically migrated**.

Implementation follows the official [Annotations Extensibility](https://learn.chatgpt.com/docs/annotations-extensibility)
and [Site tools](https://learn.chatgpt.com/docs/webmcp) documentation. State/renderer
tests and DOM bridge contract tests are included; real built-in-browser delivery
still requires end-to-end acceptance on a supported client. Do not confuse a
mocked `accepted` response with a real message being sent.

## Legacy standalone app / Python SDK (v0.1)

The instructions below run the original local app, which uses scripted demo
responses or a separately configured model API. They are not the new agent-taught
workflow above.

## Start the legacy app

Python 3.10+ is required. From the extracted or cloned repository:

```bash
python3 -m learning_harness.server serve --demo
```

Open **http://127.0.0.1:8765**. Choose **打开示例**, select text within a paragraph,
and write a question below the document. Demo replies are explicitly labeled,
scripted explanations of MoE routing; they do not answer arbitrary questions.

No Python runtime dependencies, account, API key, Node, or build step are required
for the demo. The source package has not been published to PyPI.

Optional local installation:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
learning-harness serve --demo
```

## Connect a real model

Configure any endpoint implementing the OpenAI-compatible Chat Completions
request/response shape and capable of following the JSON-output instruction.
In bash/zsh, enter the secret without putting it in shell history:

```bash
export LH_BASE_URL="https://api.openai.com/v1"
export LH_MODEL="YOUR_AVAILABLE_MODEL_ID"
read -s LH_API_KEY
export LH_API_KEY
python3 -m learning_harness.server serve
```

After `read -s LH_API_KEY`, paste your key and press Enter. Omit `--demo`.
The server reads the key from its environment; it is not sent to the browser,
saved in SQLite, or included in exported state. Your passage, question, thread,
and relevant learning state are sent to the configured model endpoint.

For a compatible local server, set `LH_BASE_URL` to its localhost `/v1` URL,
set its actual model ID, and leave `LH_API_KEY` unset if authentication is not
required. HTTP is accepted only on localhost; other endpoints require HTTPS.

Compatibility means an HTTP schema, not a promise that every provider or model
behaves identically. Claude/Gemini native APIs require a custom adapter or a
compatible gateway. ChatGPT/Claude website conversations are not wrapped by this
MVP. This release does not provide subscription login, OAuth, or an MCP server.

## What works

- Stable paragraph IDs and Unicode text offsets for anchored annotations.
- Persistent questions, follow-up threads, explicit resolve/reopen actions.
- SQLite sessions with automatic resume, multiple documents, and JSON export.
- Learner-approved prerequisite branches and a visible return stack.
- Model-independent context construction and validated response proposals.
- Understanding evidence kept separate from merely receiving an explanation.
- A responsive document + margin client; plain text is rendered safely.
- Localhost binding, host checks and per-process request tokens for writes.

Create a document by pasting text separated into paragraphs by blank lines.
The source stays stable in v0.1; the annotations and state evolve. Formula text
is supported as plain text, but there is no LaTeX renderer yet.

## Use the Python library

```python
from learning_harness import LearningSession, Store, DemoModel

store = Store("learning.sqlite3")
session = LearningSession.create(
    store,
    goal="Understand routing",
    paragraphs=["A router selects experts and weights their outputs."],
)
block = session.state["document"]["blocks"][0]
question = session.annotate(
    block_id=block["id"], start=2, end=8, quote="router",
    question="How can the router learn?",
)
session.step(DemoModel(), question["id"])
session.resolve(question["id"])
restored = LearningSession.load(store, session.state["id"])
```

Replace `DemoModel()` with `CompatibleModel()` to use the configured endpoint.
For other APIs, implement one method:

```python
class MyModel:
    name = "my-provider/my-model"

    def generate(self, context: dict) -> dict:
        # Call the provider with the context and your teaching instructions.
        return {"answer": "A scoped explanation", "prerequisites": []}
```

## Philosophy and enforcement

| Principle | v0.1 behavior |
|---|---|
| Confusion persists | Questions have stable anchors and explicit open/resolved state. |
| Keep the learner oriented | Entering a prerequisite preserves the parent on a stack. |
| Learners control progress | Models propose prerequisites; learners accept them. |
| Explanation is not mastery | AI replies only move unseen → exposed; learner explanations produce self_reported. |
| Limit unnecessary expansion | Runtime caps prerequisite proposals to one; concision and conceptual load within prose are prompt guidance, not hard guarantees. |
| Preserve content | Model replies cannot rewrite the document. |
| Portable state | Versioned JSON snapshots; adapters do not own the state. |

`core.py` owns state transitions; `models.py` owns model calls; `server.py` is a
small transport layer; `static/` is the reference client. See
[the protocol](docs/protocol.md) for exact boundaries and limitations.

## Persistence and portability

The default database is `~/.learning-harness/learning.sqlite3`. Restarting the
server preserves your documents and questions. Use `--db PATH` for another file
or `--port 8877` if the default port is occupied. Stop with Ctrl+C.

The **导出状态** button downloads a session JSON snapshot, including original
content, questions, evidence, and history. There is no UI import yet. For a full
backup, stop the server and copy the SQLite file; restore it using `--db`.

The server is a single-user localhost application. Do not expose it as a public
multi-user service; it has no account system or production deployment layer.

## Verification

```bash
python3 -m unittest discover -s tests -v
node --check learning_harness/static/app.js  # optional; needs Node
node tests/test_work_state.cjs               # v0.2 state contract
npm ci --ignore-scripts                     # optional DOM test dependencies
npm test                                   # state + mocked host bridge tests
```

Tests cover anchored Unicode spans, persistence, invalid model output rollback,
explicit mastery semantics, navigation, HTTP flow, cross-origin rejection, and
the adapter's HTTP contract against a local mock provider. No paid API key is
needed. Real provider responses and browser visual layout still need validation
in your own environment; the initial build environment had no browser binary.

## Roadmap

- Document revision and anchor migration; annotate nested explanations.
- Import/export round trips and interoperable schema validation.
- Native provider adapters, streaming, and MCP integration.
- Evidence-based assessment with auditable evaluator provenance.
- Learning-policy evaluation rather than claims of guaranteed pedagogy.

MIT licensed. Contributions welcome; keep core independent of the renderer and
avoid promoting learner mastery from generated explanations alone.

---

## 中文：旧版独立应用快速使用

1. 下载解压，在终端进入 `learning-harness` 文件夹。
2. 运行 `python3 -m learning_harness.server serve --demo`。
3. 浏览器打开 `http://127.0.0.1:8765`，点击「打开示例」。
4. 在同一段正文中划选文字，在下方写问题，点击「留下批注并提问」。
5. 右侧继续追问、进入前置概念、返回、解决问题；刷新后仍保留。
6. 想回答自己的真实问题，按上面的模型配置设置 API 后重新启动，不带 `--demo`。

已提供本地网页与 Python SDK；还没有直接嵌入 ChatGPT/Claude 的插件。
