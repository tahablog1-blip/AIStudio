"""Project folders, manifest, versioning and the inter-agent message board."""
import json
import shutil
import time
from pathlib import Path

from .core import ROOT, StudioError, ensure_dir, read_json, write_json

PROJECTS = ROOT / "projects"
STATUSES = ("pending", "running", "done", "failed", "blocked", "needs_review", "approved", "rejected")


class Project:
    def __init__(self, path):
        self.path = Path(path)
        if not (self.path / "manifest.json").exists():
            raise StudioError(f"not a studio project: {self.path}")

    # ---------- creation ----------
    @classmethod
    def create(cls, name, brief="", client="", raw_files=(), base=None):
        slug = "".join(c if c.isalnum() or c in "-_" else "-" for c in name).strip("-").lower() or "project"
        path = Path(base or PROJECTS) / slug
        if (path / "manifest.json").exists():
            raise StudioError(f"project exists: {path}")
        for d in ("raw", "work", "review", "deliver", "board", "versions"):
            ensure_dir(path / d)
        raw = []
        for f in raw_files:
            dst = path / "raw" / Path(f).name
            shutil.copy2(f, dst)
            raw.append(dst.name)
        write_json(path / "manifest.json", {
            "name": name, "slug": slug, "client": client, "brief": brief, "created": time.time(),
            "raw": raw, "deliverables": [], "tasks": {}, "history": [], "approved_version": None})
        return cls(path)

    # ---------- manifest ----------
    @property
    def m(self):
        return read_json(self.path / "manifest.json")

    def save(self, m):
        write_json(self.path / "manifest.json", m)

    def event(self, m, who, what):
        m["history"].append({"t": round(time.time(), 2), "who": who, "what": what})

    def add_task(self, tid, role, title, action=None, deps=(), outputs=(), max_attempts=2, review_by=None, notes=""):
        m = self.m
        if tid in m["tasks"]:
            raise StudioError(f"duplicate task id: {tid}")
        m["tasks"][tid] = {"role": role, "title": title, "deps": list(deps), "status": "pending",
                           "attempts": 0, "max_attempts": max_attempts, "action": action,
                           "outputs": list(outputs), "versions": [], "review_by": review_by,
                           "notes": notes, "error": None}
        self.event(m, "executive-producer", f"task {tid} -> {role}")
        self.save(m)

    def set_status(self, tid, status, who=None, error=None, version_dir=None, result=None):
        assert status in STATUSES, status
        m = self.m
        t = m["tasks"][tid]
        t["status"] = status
        t["error"] = error
        if version_dir:
            t["versions"].append({"dir": str(Path(version_dir).relative_to(self.path)), "t": round(time.time(), 2),
                                  "result": result})
        self.event(m, who or t["role"], f"{tid}: {status}" + (f" ({error[:120]})" if error else ""))
        self.save(m)

    def new_version_dir(self, tid):
        base = self.path / "work" / tid
        n = len(list(base.glob("v*"))) + 1 if base.exists() else 1
        return ensure_dir(base / f"v{n:03d}")

    def latest(self, tid, name=None):
        """Path of a task's primary (or named) output in its latest version."""
        t = self.m["tasks"].get(tid)
        if not t or not t["versions"]:
            raise StudioError(f"task {tid} has no output yet")
        v = self.path / t["versions"][-1]["dir"]
        res = t["versions"][-1].get("result") or {}
        if name:
            return str(v / name) if not res.get(name) else res[name]
        return res.get("output") or str(v / (t["outputs"][0] if t["outputs"] else ""))

    # ---------- board ----------
    def post(self, frm, to, text, files=()):
        line = {"t": round(time.time(), 2), "from": frm, "to": to, "text": text, "files": list(files)}
        with open(self.path / "board" / "messages.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")
        return line

    def inbox(self, role=None):
        p = self.path / "board" / "messages.jsonl"
        if not p.exists():
            return []
        msgs = [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
        return [x for x in msgs if role in (None, x["to"], "all")]

    # ---------- progress ----------
    def progress(self):
        ts = self.m["tasks"].values()
        if not ts:
            return 0.0
        done = sum(1 for t in ts if t["status"] in ("done", "approved"))
        return round(100 * done / len(ts), 1)


def open_project(name_or_path):
    p = Path(name_or_path)
    if not (p / "manifest.json").exists():
        p = PROJECTS / name_or_path
    return Project(p)


def deliver(project_path, files, out_dir, notes=""):
    """Executive producer sign-off: copy approved files to deliver/ and write a delivery note."""
    pr = Project(project_path)
    dst = pr.path / "deliver"
    copied = []
    for f in (files if isinstance(files, (list, tuple)) else [files]):
        if f and Path(f).exists():
            shutil.copy2(f, dst / Path(f).name)
            copied.append(Path(f).name)
    m = pr.m
    m["approved_version"] = {"t": round(time.time(), 2), "files": copied}
    pr.event(m, "executive-producer", f"approved & delivered {len(copied)} files")
    pr.save(m)
    note = Path(out_dir) / "delivery_note.md"
    note.write_text("# مذكرة التسليم\n\n" + notes + "\n\n" + "\n".join(f"- {c}" for c in copied), encoding="utf-8")
    return {"output": str(note), "files": copied}
