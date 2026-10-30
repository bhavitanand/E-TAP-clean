"""Structure checks for the GitLab Duo Agent Platform files (flows, skills, MCP config).

These cannot prove a flow runs inside GitLab (it never has), but they catch the mistakes we can catch
locally: a prompt or router that points at nothing, a missing entry point, a tool name nobody has seen.
"""
import json
import re
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
FLOWS = sorted((ROOT / ".gitlab" / "duo" / "flows").glob("*.yaml"))

# Tool names from GitLab's published flow registry documentation.
PUBLISHED_TOOLS = {
    "read_file", "create_file_with_contents", "edit_file", "list_dir", "find_files",
    "get_repository_file", "get_repository_files", "list_repository_tree",
    "get_issue", "create_issue", "get_merge_request", "create_merge_request_note", "run_command",
    "list_merge_request_diffs",  # appears in the flow editor's own template
}
# Not in the published list; each needs checking against a real project once GitLab access exists.
UNVERIFIED_TOOLS = {"get_pipeline_failing_jobs", "create_issue_note"}


def load(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


class FlowFileTests(unittest.TestCase):
    def test_the_flows_exist(self):
        self.assertEqual({p.stem for p in FLOWS},
                         {"detection-engineer", "mr-reviewer", "pipeline-triage", "incident-responder"})

    def test_every_flow_is_wired_up(self):
        for path in FLOWS:
            with self.subTest(flow=path.name):
                flow = load(path)
                self.assertEqual(flow["version"], "v1")
                self.assertEqual(flow["environment"], "ambient")
                for unsupported in ("name", "description", "product_group"):
                    self.assertNotIn(unsupported, flow, "rejected by custom flows")
                components = {c["name"]: c for c in flow["components"]}
                prompts = {p["prompt_id"] for p in flow["prompts"]}
                self.assertEqual(len(components), len(flow["components"]), "duplicate component names")
                self.assertIn(flow["flow"]["entry_point"], components)
                for component in components.values():
                    self.assertIn(component["type"], {"AgentComponent", "OneOffComponent"})
                    self.assertIn(component["prompt_id"], prompts)
                routed_from = set()
                for router in flow["routers"]:
                    self.assertIn(router["from"], components)
                    routed_from.add(router["from"])
                    self.assertIn(router.get("to", "end"), set(components) | {"end"})
                self.assertEqual(routed_from, set(components), "every component needs a way onward")
                self.assertEqual(sum(r.get("to") == "end" for r in flow["routers"]), 1, "exactly one way to end")

    def test_inputs_refer_to_real_components(self):
        for path in FLOWS:
            with self.subTest(flow=path.name):
                flow = load(path)
                names = {c["name"] for c in flow["components"]}
                for component in flow["components"]:
                    for item in component.get("inputs", []):
                        ref = item["from"] if isinstance(item, dict) else item
                        match = re.fullmatch(r"context:([a-z_]+)\.final_answer", ref)
                        if match:
                            self.assertIn(match.group(1), names)
                        else:
                            self.assertIn(ref, {"context:goal", "context:project_id"})

    def test_prompt_placeholders_match_inputs(self):
        for path in FLOWS:
            with self.subTest(flow=path.name):
                flow = load(path)
                prompts = {p["prompt_id"]: p for p in flow["prompts"]}
                for component in flow["components"]:
                    provided = {"goal"}
                    for item in component.get("inputs", []):
                        if isinstance(item, dict):
                            provided.add(item["as"])
                    template = prompts[component["prompt_id"]]["prompt_template"]
                    used = set(re.findall(r"\{\{(\w+)\}\}", template["system"] + template["user"]))
                    self.assertLessEqual(used, provided, f"{component['name']} uses an input it does not receive")

    def test_tools_are_published_or_flagged(self):
        seen_unverified = set()
        for path in FLOWS:
            with self.subTest(flow=path.name):
                for component in load(path)["components"]:
                    for tool in component.get("toolset", []):
                        self.assertIn(tool, PUBLISHED_TOOLS | UNVERIFIED_TOOLS)
                        if tool in UNVERIFIED_TOOLS:
                            seen_unverified.add(tool)
                            self.assertIn(tool, path.read_text(encoding="utf-8").split("version:")[0],
                                          "unverified tools must be named in the file's header comment")
        self.assertEqual(seen_unverified, UNVERIFIED_TOOLS, "the unverified list should match what is used")

    def test_read_only_flows_have_no_write_tools(self):
        write_tools = {"create_file_with_contents", "edit_file", "create_issue"}
        for stem in ("incident-responder", "mr-reviewer", "pipeline-triage"):
            with self.subTest(flow=stem):
                flow = load(ROOT / ".gitlab" / "duo" / "flows" / f"{stem}.yaml")
                used = {t for c in flow["components"] for t in c.get("toolset", [])}
                self.assertFalse(used & write_tools, "these flows only diagnose and comment")


class SkillAndConfigTests(unittest.TestCase):
    def test_skill_has_required_metadata(self):
        for skill in (ROOT / "skills").glob("*/SKILL.md"):
            with self.subTest(skill=skill.parent.name):
                text = skill.read_text(encoding="utf-8")
                meta = yaml.safe_load(text.split("---")[1])
                self.assertEqual(meta["name"], skill.parent.name)
                self.assertGreater(len(meta["description"]), 20)

    def test_mcp_config_points_at_the_server(self):
        config = json.loads((ROOT / ".gitlab" / "duo" / "mcp.json").read_text(encoding="utf-8"))
        server = config["mcpServers"]["etap"]
        self.assertEqual(server["type"], "stdio")
        self.assertTrue((ROOT / server["args"][0]).is_file())

    def test_runbook_covers_the_probes_the_flow_uses(self):
        runbook = (ROOT / "docs" / "incident-runbook.md").read_text(encoding="utf-8")
        self.assertIn("/health", runbook)
        self.assertIn("/ready", runbook)

    def test_pipeline_is_valid_and_has_the_expected_stages(self):
        ci = yaml.safe_load((ROOT / ".gitlab-ci.yml").read_text(encoding="utf-8"))
        self.assertEqual(ci["stages"], ["verify", "test", "package", "release"])
        for name, job in ci.items():
            if isinstance(job, dict) and "script" in job:
                self.assertIn(job["stage"], ci["stages"], name)


if __name__ == "__main__":
    unittest.main()
