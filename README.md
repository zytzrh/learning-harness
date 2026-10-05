# Learning Harness · Margin

An open-source, local-first learning runtime with an annotatable document client.

**Select → question → clarify → resolve.** Keep confusion attached to the passage
that caused it, preserve a return path when exploring prerequisites, and carry
learning state between sessions and model adapters.

This is a working **v0.1 MVP**, not a validated adaptive tutor. The browser client
is called **Margin**; the independent Python library is `learning_harness`.

## Start in one command

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

## 中文快速使用

1. 下载解压，在终端进入 `learning-harness` 文件夹。
2. 运行 `python3 -m learning_harness.server serve --demo`。
3. 浏览器打开 `http://127.0.0.1:8765`，点击「打开示例」。
4. 在同一段正文中划选文字，在下方写问题，点击「留下批注并提问」。
5. 右侧继续追问、进入前置概念、返回、解决问题；刷新后仍保留。
6. 想回答自己的真实问题，按上面的模型配置设置 API 后重新启动，不带 `--demo`。

已提供本地网页与 Python SDK；还没有直接嵌入 ChatGPT/Claude 的插件。
