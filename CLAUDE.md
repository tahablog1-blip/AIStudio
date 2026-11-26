# AI Studio — instructions for Claude

This repo is an executable AI video production studio (31 role agents in `.claude/agents/`, skills in `.claude/skills/`).
- First time in a session: run `bash bootstrap.sh` (add `--with-3d` only if 3D is needed). Then `python -m studio roles`.
- For any video request act as `executive-producer`: create a project (`python -m studio new`), plan (`plan <slug> promo` or `add-task`), `validate`, `run`, then **watch sampled frames yourself before delivery** — automated QC passed while visible defects existed in testing (docs/03_test_report.md).
- Roles may only run their authorised modules (`studio/roles.py`); use `python -m studio do <module.fn> --role <role> --args '<json>'`.
- Be explicit about unavailable tools (Premiere, After Effects, Resolve, …): see docs/capabilities.md; deliver FCP7 XML/EDL for human finishing.
- Never overwrite versions; outputs go to `work/<task>/vNNN`, deliverables to `deliver/`.
