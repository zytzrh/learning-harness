"""JSON state + SQLite persistence, independent of transport and renderer."""
import copy
import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone


def uid():
    return uuid.uuid4().hex


def now():
    return datetime.now(timezone.utc).isoformat()


def required(value, label, maximum=12000):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"{label} must contain 1–{maximum} characters")
    return value.strip()


class Store:
    def __init__(self, path="learning.sqlite3"):
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.lock = threading.RLock()
        self.db.execute("CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, state TEXT NOT NULL)")
        self.db.commit()

    def save(self, state):
        with self.lock, self.db:
            self.db.execute("INSERT INTO sessions VALUES (?, ?) ON CONFLICT(id) DO UPDATE SET state=excluded.state", (state["id"], json.dumps(state, ensure_ascii=False)))

    def load(self, sid):
        with self.lock:
            row = self.db.execute("SELECT state FROM sessions WHERE id=?", (sid,)).fetchone()
        if row is None:
            raise ValueError("Session not found")
        return json.loads(row[0])

    def list(self):
        with self.lock:
            states = [json.loads(r[0]) for r in self.db.execute("SELECT state FROM sessions")]
        return sorted([{"id": s["id"], "goal": s["goal"], "updated_at": s["updated_at"]} for s in states], key=lambda x: x["updated_at"], reverse=True)


class LearningSession:
    """Single-writer session. Hosts serialize mutations; model output is untrusted."""
    def __init__(self, store, state):
        self.store, self.state = store, state

    @classmethod
    def create(cls, store, goal, paragraphs, title=None):
        goal = required(goal, "Goal", 500)
        if not isinstance(paragraphs, list) or not 1 <= len(paragraphs) <= 100:
            raise ValueError("Provide 1–100 paragraphs")
        blocks = [{"id": uid(), "text": required(p, "Paragraph")} for p in paragraphs]
        cid = uid()
        state = {"schema_version": 1, "id": uid(), "goal": goal, "title": title or goal,
                 "document": {"revision": 1, "blocks": blocks},
                 "concepts": [{"id": cid, "name": goal, "status": "unseen", "evidence": []}],
                 "stack": [cid], "annotations": [], "events": [],
                 "policy": {"frontier_budget": 1}, "updated_at": now()}
        session = cls(store, state)
        session._event("session_created", {"goal": goal})
        return session

    @classmethod
    def load(cls, store, sid):
        return cls(store, store.load(sid))

    def _event(self, kind, data):
        self.state["updated_at"] = now()
        self.state["events"].append({"id": uid(), "at": now(), "type": kind, "data": data})
        self.store.save(self.state)

    def concept(self, cid):
        return next((c for c in self.state["concepts"] if c["id"] == cid), None)

    def annotation(self, aid):
        a = next((a for a in self.state["annotations"] if a["id"] == aid), None)
        if a is None:
            raise ValueError("Annotation not found")
        return a

    def annotate(self, block_id, start, end, quote, question):
        block = next((b for b in self.state["document"]["blocks"] if b["id"] == block_id), None)
        if block is None or type(start) is not int or type(end) is not int or not 0 <= start < end <= len(block["text"]) or block["text"][start:end] != quote:
            raise ValueError("Selection does not match the document. Select text again.")
        a = {"id": uid(), "anchor": {"block_id": block_id, "revision": self.state["document"]["revision"], "start": start, "end": end, "quote": quote},
             "question": required(question, "Question", 4000), "status": "open", "concept_id": self.state["stack"][-1], "thread": [], "created_at": now()}
        self.state["annotations"].append(a)
        self._event("annotation_created", {"annotation_id": a["id"]})
        return a

    def context(self, aid, followup=None):
        a = self.annotation(aid)
        block = next(b for b in self.state["document"]["blocks"] if b["id"] == a["anchor"]["block_id"])
        return copy.deepcopy({"goal": self.state["goal"], "action": "CLARIFY", "policy": self.state["policy"],
                              "stack": [self.concept(c) for c in self.state["stack"]],
                              "concepts": self.state["concepts"], "passage": block["text"], "annotation": a, "followup": followup})

    def step(self, model, aid, followup=None):
        if followup is not None:
            followup = required(followup, "Follow-up", 4000)
        a = self.annotation(aid)
        result = model.generate(self.context(aid, followup))
        if not isinstance(result, dict):
            raise ValueError("Model must return an object")
        answer = required(result.get("answer"), "Model answer", 30000)
        proposed = result.get("prerequisites", [])
        if not isinstance(proposed, list) or any(not isinstance(p, str) for p in proposed):
            raise ValueError("Invalid prerequisite proposals")
        # Proposals never silently change navigation, mastery, or the document.
        proposals = list(dict.fromkeys(p.strip()[:200] for p in proposed if p.strip()))[:self.state["policy"]["frontier_budget"]]
        if followup:
            a["thread"].append({"role": "user", "text": followup, "at": now()})
        a["thread"].append({"role": "assistant", "text": answer, "at": now(), "prerequisites": proposals, "model": model.name})
        c = self.concept(a["concept_id"])
        if c["status"] == "unseen":
            c["status"] = "exposed"
        self._event("explanation_added", {"annotation_id": aid, "model": model.name, "proposals": proposals})
        return result

    def resolve(self, aid, resolved=True):
        if type(resolved) is not bool:
            raise ValueError("resolved must be boolean")
        self.annotation(aid)["status"] = "resolved" if resolved else "open"
        self._event("annotation_resolved" if resolved else "annotation_reopened", {"annotation_id": aid})

    def push(self, name):
        name = required(name, "Concept", 200)
        existing = next((c for c in self.state["concepts"] if c["name"].casefold() == name.casefold()), None)
        if existing and existing["id"] in self.state["stack"]:
            raise ValueError("This concept is already in the active path")
        c = existing or {"id": uid(), "name": name, "status": "unseen", "evidence": []}
        parent = self.state["stack"][-1]
        if existing is None:
            self.state["concepts"].append(c)
        self.state.setdefault("prerequisites", [])
        edge = {"concept": parent, "requires": c["id"]}
        if edge not in self.state["prerequisites"]:
            self.state["prerequisites"].append(edge)
        self.state["stack"].append(c["id"])
        self._event("prerequisite_entered", edge)

    def back(self):
        if len(self.state["stack"]) <= 1:
            raise ValueError("Already at the learning goal")
        cid = self.state["stack"].pop()
        self._event("returned", {"from": cid, "to": self.state["stack"][-1]})

    def record_understanding(self, cid, explanation):
        c = self.concept(cid)
        if c is None:
            raise ValueError("Concept not found")
        explanation = required(explanation, "Your explanation", 8000)
        c["status"] = "self_reported"
        c["evidence"].append({"kind": "learner_explanation", "text": explanation, "at": now(), "verified": False})
        self._event("understanding_reported", {"concept_id": cid})
