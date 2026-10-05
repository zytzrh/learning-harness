"""Local-only reference web client. No third-party runtime dependencies."""
import argparse
import json
import os
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from .core import LearningSession, Store
from .models import DemoModel, CompatibleModel

DEMO = [
    "循环 Transformer：把一组共享参数的层重复应用于隐藏状态，让计算深度不必等于独立参数层的数量。重复次数可以固定，也可以由模型决定。",
    "自适应计算：不同 token 可能需要不同的计算量。路由器可以决定 token 是否继续下一轮，但离散选择的训练方式取决于具体架构与目标。",
    "类比 MoE：常见的 top-k routing 先选出少量专家，再用路由权重组合它们的输出。选择专家的索引是离散的，但被选中专家对应的权重仍可能保留可微的梯度路径。",
    "阅读时请划选一句你不确定的话，留下问题。解释会留在这条批注中。需要补充前置知识时，可以进入一个分支，然后返回原来的学习目标。"
]


def make_handler(store, model, port):
    mutation_lock = threading.RLock()
    token = secrets.token_urlsafe(32)
    static = Path(__file__).parent / "static"
    allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
    allowed_origins = {"http://" + h for h in allowed_hosts}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def send(self, status, data, content_type="application/json; charset=utf-8"):
            if not isinstance(data, bytes):
                data = json.dumps(data, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(data)

        def safe_host(self):
            if self.headers.get("Host") not in allowed_hosts:
                self.send(403, {"error": "Localhost access only"})
                return False
            return True

        def do_GET(self):
            if not self.safe_host():
                return
            path = urlparse(self.path)
            if path.path == "/api/bootstrap":
                self.send(200, {"token": token, "model": model.name, "demo": isinstance(model, DemoModel), "sessions": store.list()})
            elif path.path == "/api/session":
                try:
                    self.send(200, store.load(parse_qs(path.query).get("id", [""])[0]))
                except ValueError as exc:
                    self.send(404, {"error": str(exc)})
            elif path.path in {"/", "/app.js", "/style.css"}:
                name = "index.html" if path.path == "/" else path.path[1:]
                mime = {"index.html": "text/html", "app.js": "text/javascript", "style.css": "text/css"}[name]
                self.send(200, (static / name).read_bytes(), mime + "; charset=utf-8")
            else:
                self.send(404, {"error": "Not found"})

        def do_POST(self):
            if not self.safe_host():
                return
            if self.headers.get("X-Learning-Token") != token or self.headers.get("Origin") not in allowed_origins:
                self.send(403, {"error": "Reload the local app before submitting"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 1000000:
                    raise ValueError("Invalid request size")
                data = json.loads(self.rfile.read(length))
                if not isinstance(data, dict):
                    raise ValueError("Expected an object")
                with mutation_lock:
                    if self.path == "/api/create":
                        session = LearningSession.create(store, data.get("goal", "理解循环 Transformer"), DEMO if data.get("demo") else data.get("paragraphs"))
                    else:
                        session = LearningSession.load(store, data.get("session_id", ""))
                        if self.path == "/api/annotate":
                            session.annotate(data.get("block_id"), data.get("start"), data.get("end"), data.get("quote"), data.get("question"))
                        elif self.path == "/api/ask":
                            session.step(model, data.get("annotation_id"), data.get("followup"))
                        elif self.path == "/api/resolve":
                            session.resolve(data.get("annotation_id"), data.get("resolved", True))
                        elif self.path == "/api/push":
                            session.push(data.get("name"))
                        elif self.path == "/api/back":
                            session.back()
                        elif self.path == "/api/understanding":
                            session.record_understanding(data.get("concept_id"), data.get("explanation"))
                        else:
                            self.send(404, {"error": "Not found"})
                            return
                    self.send(200, session.state)
            except (ValueError, TypeError) as exc:
                self.send(400, {"error": str(exc)})
            except Exception:
                self.send(500, {"error": "The operation failed. Your saved session is preserved; reload and retry."})
    return Handler


def main():
    parser = argparse.ArgumentParser(description="Start the local learning workspace")
    parser.add_argument("command", choices=["serve"], nargs="?", default="serve")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--db", default=str(Path.home() / ".learning-harness" / "learning.sqlite3"))
    parser.add_argument("--demo", action="store_true", help="Use explicitly labeled scripted responses")
    args = parser.parse_args()
    Path(args.db).expanduser().parent.mkdir(parents=True, exist_ok=True)
    store = Store(str(Path(args.db).expanduser()))
    model = DemoModel() if args.demo or not os.getenv("LH_MODEL") else CompatibleModel()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(store, model, args.port))
    print(f"Learning Harness → http://127.0.0.1:{args.port} | {model.name}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()


if __name__ == "__main__":
    main()
