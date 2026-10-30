# 2026-10-25 — Hackathon concept: a detection-engineering workflow on GitLab Duo Agent Platform

**Type:** Proposal (hackathon copy of the repository). Needs the team's confirmation.

## The idea
E-TAP's behaviour rules (`backend/sandbox/rules/*.toml`) are small, testable files. That makes rule writing a good job for an agent, with a pipeline as the judge.

1. Someone opens a GitLab issue describing a suspicious email sample or behaviour and assigns the flow's service account to it (trigger: *Assign*).
2. **rule_writer** (agent) reads the issue and the rule README, writes one new original rule with matching and non-matching test cases, and runs the rule tests until they pass.
3. The merge request runs the pipeline: backend, frontend and extension tests, the rule tests, SAST, secret detection and dependency scanning.
4. **reviewer** (agent) checks originality, test quality and over-broad matching, and posts its verdict on the merge request.
5. Merge builds the API image; production deploy (Render) is a manual play button.

Files: `.gitlab/duo/flows/detection-engineer.yaml` (flow), `.gitlab-ci.yml` (pipeline).

## Refocus on "life after code" (added after reading the contributors page)
The challenge is automating what happens after the code is written. Writing a rule is closer to creating code, so it stays as one flow that feeds the loop, and three flows were added for the later stages:

| Flow | Trigger | Stage | What it does |
| --- | --- | --- | --- |
| `mr-reviewer` | assigned as reviewer | verify, govern | Reviews a merge request, runs the matching tests, posts a verdict with what it did not check. |
| `pipeline-triage` | pipeline event | verify, release | Finds the failing job, explains the cause, posts the smallest fix as an MR note. |
| `incident-responder` | assigned to an "E-TAP is down" issue | monitor | Runs read-only `/health` and `/ready` checks, follows `docs/incident-runbook.md`, comments in plain words. |
| `detection-engineer` | assigned to a sample issue | create | Writes one original rule with tests. |

Also: `skills/etap-detection-rules/SKILL.md` (project skill that teaches agents our rule format), `mcp_server/` and `.gitlab/duo/mcp.json` (E-TAP as a tool). `backend/tests/test_duo_files.py` checks the flows' wiring locally; it cannot prove a flow runs in GitLab.

## Lifecycle stages touched (of nine)
plan (issue), create (rule and MR), verify (tests, MR review, failure triage), package (image build), secure (scanners), release (manual Render deploy), configure (pipeline and flows as code), monitor (probes and the incident responder; GitLab Observability is optional and free in the provisioned subgroup), govern (human approval before production, read-only incident flow, MIT-only rule policy). All nine are touched, but only on paper until the flows run in GitLab.

## Autonomy level
Recommended: **Supervised** (a human merges and presses production). Hands-off would need the agent to merge and promote on its own when the pipeline is green. That is possible but riskier to demonstrate; decide after the first real run.

## Decisions (taken by Bhavit, who was authorised by the team on 2026-10-25)
- **Supervised.** A human merges and approves production. It demos reliably in under three minutes and the approval gate is the governance story. Hands-off stays a stretch goal only after a clean real run.
- **MCP server: yes.** `mcp_server/` exposes `analyze_email`, `get_report` and `list_detection_rules` to Duo agents; `.gitlab/duo/mcp.json` registers it. It is local, tested, and covers the MCP-client requirement.
- **Google Cloud: dropped** (same day). Bhavit created a project, but both billing accounts were closed, Cloud Run needs a card, Google has no hard spending cap and the API has no login, so the team chose not to risk a bill. The live URL stays on Render and Vercel; the Google Cloud bonus (up to +0.2) is forgone. `deploy/cloudrun/` stays as optional, untested files (scale-to-zero). The pipeline's deploy job calls a Render deploy hook instead.

## Not verified
- The flow has never run in GitLab (account approval pending). It follows the published v1 schema; the tool names `create_merge_request_note` and `run_command` were in GitLab's published list, but whether the flow can open a merge request itself is unknown, so the writer currently leaves the change for a person or the trigger to turn into an MR.
- The pipeline and Cloud Run files are YAML-checked only: nothing was run on GitLab or Google Cloud.
- The `frontend.Dockerfile` and `deploy.sh` were not built or run (no Docker or gcloud used here).
