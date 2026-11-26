"""`python -m studio <command>` — the single interface every agent uses."""
import argparse
import importlib
import json
import sys

from .core import StudioError
from .orchestrator import run_project, status_table, validate
from .project import Project, open_project
from .roles import DEPTS, EXTERNAL, ROLES


def _args(s):
    return json.loads(s) if s else {}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="studio", description="AI Studio CLI")
    sp = ap.add_subparsers(dest="cmd", required=True)
    a = sp.add_parser("new"); a.add_argument("name"); a.add_argument("--brief", default=""); a.add_argument("--client", default="")
    a.add_argument("--raw", nargs="*", default=[])
    a = sp.add_parser("plan"); a.add_argument("project"); a.add_argument("template"); a.add_argument("--params", default="{}")
    a = sp.add_parser("add-task"); a.add_argument("project"); a.add_argument("id"); a.add_argument("--role", required=True)
    a.add_argument("--title", required=True); a.add_argument("--fn", required=True); a.add_argument("--args", default="{}")
    a.add_argument("--deps", nargs="*", default=[]); a.add_argument("--review-by")
    a = sp.add_parser("validate"); a.add_argument("project")
    a = sp.add_parser("run"); a.add_argument("project"); a.add_argument("--workers", type=int, default=4)
    a.add_argument("--only", nargs="*"); a.add_argument("--hold-reviews", action="store_true")
    a = sp.add_parser("status"); a.add_argument("project")
    a = sp.add_parser("retry"); a.add_argument("project"); a.add_argument("task")
    a = sp.add_parser("review"); a.add_argument("project"); a.add_argument("task"); a.add_argument("--by", required=True)
    a.add_argument("--decision", choices=["approve", "reject"], required=True); a.add_argument("--note", default="")
    a = sp.add_parser("post"); a.add_argument("project"); a.add_argument("--from", dest="frm", required=True)
    a.add_argument("--to", required=True); a.add_argument("text")
    a = sp.add_parser("inbox"); a.add_argument("project"); a.add_argument("--role")
    a = sp.add_parser("do"); a.add_argument("fn", help="module.function"); a.add_argument("--role", required=True)
    a.add_argument("--args", default="{}")
    sp.add_parser("roles")
    a = sp.add_parser("role"); a.add_argument("id")
    sp.add_parser("capabilities")
    ns = ap.parse_args(argv)
    try:
        out = dispatch(ns)
        if out is not None:
            print(out if isinstance(out, str) else json.dumps(out, ensure_ascii=False, indent=2))
    except StudioError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(2)


def dispatch(ns):
    if ns.cmd == "new":
        pr = Project.create(ns.name, ns.brief, ns.client, ns.raw)
        return f"created {pr.path}"
    if ns.cmd == "plan":
        from .pipelines import TEMPLATES
        pr = open_project(ns.project)
        TEMPLATES[ns.template](pr, **_args(ns.params))
        probs = validate(pr)
        return status_table(pr) + ("\nINVALID:\n- " + "\n- ".join(probs) if probs else "\ngraph valid ✔")
    if ns.cmd == "add-task":
        pr = open_project(ns.project)
        pr.add_task(ns.id, ns.role, ns.title, action={"fn": ns.fn, "args": _args(ns.args)}, deps=ns.deps, review_by=ns.review_by)
        return "added"
    if ns.cmd == "validate":
        probs = validate(open_project(ns.project))
        return "graph valid ✔" if not probs else "INVALID:\n- " + "\n- ".join(probs)
    if ns.cmd == "run":
        return run_project(open_project(ns.project), ns.workers, ns.only, approve_reviews=not ns.hold_reviews)
    if ns.cmd == "status":
        return status_table(open_project(ns.project))
    if ns.cmd == "retry":
        pr = open_project(ns.project)
        m = pr.m
        def reset(tid):
            m["tasks"][tid].update(status="pending", attempts=0, error=None)
            for k, t in m["tasks"].items():
                if tid in t["deps"] and t["status"] in ("blocked", "failed", "done", "approved", "needs_review", "running", "rejected"):
                    reset(k)
        reset(ns.task)
        pr.event(m, "production-manager", f"retry {ns.task} (+dependents)")
        pr.save(m)
        return status_table(pr)
    if ns.cmd == "review":
        pr = open_project(ns.project)
        t = pr.m["tasks"][ns.task]
        if t.get("review_by") and t["review_by"] != ns.by and ns.by != "executive-producer":
            raise StudioError(f"{ns.by} is not the reviewer of {ns.task} ({t['review_by']})")
        pr.set_status(ns.task, "approved" if ns.decision == "approve" else "rejected", who=ns.by,
                      error=None if ns.decision == "approve" else ns.note)
        pr.post(ns.by, t["role"], f"{ns.task}: {ns.decision} — {ns.note}")
        return status_table(pr)
    if ns.cmd == "post":
        return open_project(ns.project).post(ns.frm, ns.to, ns.text)
    if ns.cmd == "inbox":
        return open_project(ns.project).inbox(ns.role)
    if ns.cmd == "do":
        role = ROLES.get(ns.role) or (_ for _ in ()).throw(StudioError(f"unknown role {ns.role}"))
        mod_name, fn_name = ns.fn.rsplit(".", 1)
        if mod_name not in role["modules"]:
            raise StudioError(f"{ns.role} is not authorised to run {ns.fn}; allowed modules: {role['modules']}")
        return getattr(importlib.import_module(f"studio.{mod_name}"), fn_name)(**_args(ns.args))
    if ns.cmd == "roles":
        return "\n".join(f"{r['id']:<22} {DEPTS[r['dept']]:<28} {r['ar']}" for r in ROLES.values())
    if ns.cmd == "role":
        return ROLES[ns.id]
    if ns.cmd == "capabilities":
        return EXTERNAL
