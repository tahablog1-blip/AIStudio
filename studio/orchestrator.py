"""Central coordinator: validates the task graph, runs tasks in parallel, retries failures,
blocks dependents, enforces review gates and keeps every output as a new version."""
import importlib
import re
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor, FIRST_COMPLETED, wait

from .core import StudioError, log
from .roles import ROLES

TEMPLATE = re.compile(r"\{(task:[\w\-]+(?::[\w.\-]+)?|raw|out|project)\}")


def resolve(value, project, out_dir):
    if isinstance(value, dict):
        return {k: resolve(v, project, out_dir) for k, v in value.items()}
    if isinstance(value, list):
        return [resolve(v, project, out_dir) for v in value]
    if not isinstance(value, str):
        return value

    def sub(mt):
        key = mt.group(1)
        if key == "raw":
            return str(project.path / "raw")
        if key == "out":
            return str(out_dir)
        if key == "project":
            return str(project.path)
        parts = key.split(":")
        return project.latest(parts[1], parts[2] if len(parts) > 2 else None)
    value = TEMPLATE.sub(sub, value)
    return _special(value, out_dir)


def _special(value, out_dir):
    """@file:path  @dur:path  @shift:timeline.json:secs  @pad:audio:secs  @cuts:edit.mp4"""
    if not value.startswith("@"):
        return value
    from pathlib import Path
    from .core import duration, ffmpeg, read_json, write_json
    kind, rest = value[1:].split(":", 1)
    if kind == "file":
        return Path(rest).read_text(encoding="utf-8")
    if kind == "dur":
        return duration(rest)
    if kind == "shift":
        path, secs = rest.rsplit(":", 1)
        tl = read_json(path)
        for s in tl:
            s["start"] = round(s["start"] + float(secs), 3)
            s["words"] = [[w, round(t + float(secs), 3)] for w, t in s.get("words", [])]
        out = Path(out_dir) / "timeline_shifted.json"
        write_json(out, tl)
        return str(out)
    if kind == "pad":
        path, secs = rest.rsplit(":", 1)
        out = Path(out_dir) / "_padded.wav"
        ms = int(float(secs) * 1000)
        ffmpeg("-i", path, "-af", f"adelay={ms}|{ms}", str(out))
        return str(out)
    if kind == "cuts":
        from .audio import spot_from_cuts
        cuts = read_json(Path(rest).parent / "cuts.json", [])
        return spot_from_cuts(cuts)
    raise StudioError(f"unknown reference {value}")


def validate(project):
    """Static checks before anything runs: unknown roles/deps, cycles, write conflicts, authority."""
    tasks = project.m["tasks"]
    problems = []
    outputs = {}
    for tid, t in tasks.items():
        role = ROLES.get(t["role"])
        if not role:
            problems.append(f"{tid}: unknown role {t['role']}")
            continue
        for d in t["deps"]:
            if d not in tasks:
                problems.append(f"{tid}: missing dependency {d}")
        act = (t.get("action") or {}).get("fn")
        if act and act.split(".")[0] not in role["modules"]:
            problems.append(f"{tid}: role {t['role']} is not authorised to run {act} (allowed: {role['modules']})")
        for o in t["outputs"]:
            key = (o if "/" in o else f"{tid}/{o}")
            if key in outputs:
                problems.append(f"output conflict: {key} written by {outputs[key]} and {tid}")
            outputs[key] = tid
        if t.get("review_by") and t["review_by"] not in ROLES:
            problems.append(f"{tid}: unknown reviewer {t['review_by']}")
    # cycle detection
    state = {}

    def visit(n, stack):
        if state.get(n) == 1:
            problems.append("dependency cycle: " + " -> ".join(stack + [n]))
            return
        if state.get(n) == 2 or n not in tasks:
            return
        state[n] = 1
        for d in tasks[n]["deps"]:
            visit(d, stack + [n])
        state[n] = 2
    for n in tasks:
        visit(n, [])
    return problems


def call_action(action, project, out_dir):
    mod_name, fn_name = action["fn"].rsplit(".", 1)
    mod = importlib.import_module(f"studio.{mod_name}")
    fn = getattr(mod, fn_name)
    kwargs = resolve(action.get("args", {}), project, out_dir)
    return fn(**kwargs)


def run_project(project, workers=4, only=None, approve_reviews=True):
    problems = validate(project)
    if problems:
        raise StudioError("task graph invalid:\n- " + "\n- ".join(problems))
    lock = threading.Lock()
    # crash recovery: tasks left "running" by an interrupted run go back to the queue
    m = project.m
    stale = [k for k, t in m["tasks"].items() if t["status"] == "running"]
    for k in stale:
        m["tasks"][k]["status"] = "pending"
        project.event(m, "production-manager", f"recovered interrupted task {k}")
    if stale:
        project.save(m)
        log(f"recovered {len(stale)} interrupted task(s): {stale}", "production-manager")

    def ready(tid, tasks):
        t = tasks[tid]
        if t["status"] not in ("pending",):
            return False
        return all(tasks[d]["status"] in ("done", "approved") for d in t["deps"])

    def execute(tid):
        t = project.m["tasks"][tid]
        role = t["role"]
        with lock:
            project.set_status(tid, "running", who=role)
        attempt = t["attempts"]
        while attempt < t["max_attempts"]:
            attempt += 1
            with lock:
                m = project.m
                m["tasks"][tid]["attempts"] = attempt
                project.save(m)
            out_dir = project.new_version_dir(tid)
            try:
                log(f"{tid} attempt {attempt}: {t['title']}", role)
                act = dict(t["action"])
                act["args"] = dict(act.get("args", {}))
                if attempt > 1:
                    act["args"].setdefault("attempt", attempt) if act.get("retry_arg") else None
                result = call_action(act, project, out_dir) or {}
                if isinstance(result, str):
                    result = {"output": result}
                gate = result.get("qc_pass")
                if gate is False:
                    raise StudioError(f"quality gate failed: {result.get('summary', '')}")
                status = "needs_review" if t.get("review_by") else "done"
                with lock:
                    project.set_status(tid, status, who=role, version_dir=out_dir, result=result)
                    if status == "needs_review":
                        project.post(role, t["review_by"], f"{tid} ready for review", [result.get("output", "")])
                        if approve_reviews:
                            project.set_status(tid, "approved", who=t["review_by"])
                return True
            except Exception as e:  # noqa
                err = f"{e}"
                log(f"{tid} failed: {err.splitlines()[0][:200]}", role)
                with lock:
                    project.post(role, "executive-producer", f"{tid} attempt {attempt} failed: {err[:300]}")
                last = err + "\n" + traceback.format_exc()[-600:]
        with lock:
            project.set_status(tid, "failed", who=role, error=last[:1500])
        return False

    with ThreadPoolExecutor(max_workers=workers) as pool:
        running = {}
        while True:
            tasks = project.m["tasks"]
            # block dependents of failed tasks
            changed = True
            while changed:
                changed = False
                for tid, t in tasks.items():
                    if t["status"] == "pending" and any(tasks[d]["status"] in ("failed", "blocked", "rejected") for d in t["deps"]):
                        project.set_status(tid, "blocked", who="production-manager")
                        tasks = project.m["tasks"]
                        changed = True
            for tid in tasks:
                if tid not in running and (only is None or tid in only) and ready(tid, tasks):
                    running[tid] = pool.submit(execute, tid)
            active = {k: f for k, f in running.items() if not f.done()}
            if not active:
                tasks = project.m["tasks"]
                if not any((only is None or tid in only) and ready(tid, tasks) for tid in tasks):
                    break
                continue
            wait(active.values(), return_when=FIRST_COMPLETED)
    return status_table(project)


def status_table(project):
    m = project.m
    rows = [f"Project: {m['name']}  —  progress {project.progress()}%"]
    for tid, t in m["tasks"].items():
        v = len(t["versions"])
        rows.append(f"  {t['status']:<12} {tid:<22} {t['role']:<26} v{v:03d}  {t['title'][:50]}")
    return "\n".join(rows)
