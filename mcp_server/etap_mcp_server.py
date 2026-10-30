"""E-TAP MCP server: lets an AI agent (for example an IDE assistant) use E-TAP as a tool.

Speaks the Model Context Protocol over stdio (newline-delimited JSON-RPC 2.0). Standard library only,
Python 3.11+. Configure the API with ETAP_API_URL (default http://127.0.0.1:5000).

Tools:
  analyze_email        analyze a .eml/.msg file in the workspace; returns verdict and score
  get_report           fetch a stored report by email_id
  list_detection_rules the behaviour rules in backend/sandbox/rules, with severity and ATT&CK ids
"""
from __future__ import annotations

import json
import os
import sys
import tomllib
import urllib.error
import urllib.request
import uuid
from pathlib import Path

PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "etap", "version": "1.0.0"}
RULES_DIR = Path(__file__).resolve().parent.parent / "backend" / "sandbox" / "rules"
MAX_FILE_BYTES = 25 * 1024 * 1024
ALLOWED_SUFFIXES = {".eml", ".msg"}

TOOLS = [
    {
        "name": "analyze_email",
        "description": "Analyze a suspicious email file with E-TAP and return its verdict (for example Likely Phishing), "
                       "risk score from 0 to 100 and report id. Use for .eml or .msg files inside the workspace.",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Path to a .eml or .msg file"}},
            "required": ["path"],
        },
    },
    {
        "name": "get_report",
        "description": "Fetch a stored E-TAP analysis report by its email_id.",
        "inputSchema": {
            "type": "object",
            "properties": {"email_id": {"type": "string"}},
            "required": ["email_id"],
        },
    },
    {
        "name": "list_detection_rules",
        "description": "List E-TAP's behaviour detection rules: id, name, severity (high rules can raise the score to 85) "
                       "and MITRE ATT&CK technique ids. Use before writing a new rule to avoid duplicates.",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


def api_url() -> str:
    return os.environ.get("ETAP_API_URL", "http://127.0.0.1:5000").rstrip("/")


def _request(req: urllib.request.Request) -> dict:
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:300]
        raise ToolError(f"E-TAP API answered {exc.code}: {detail}") from None
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ToolError(f"Could not reach the E-TAP API at {api_url()} ({exc}). Is it running?") from None


class ToolError(Exception):
    """A problem the agent should see as a tool result, not a protocol error."""


def analyze_email(path: str) -> dict:
    file = Path(path).expanduser().resolve()
    if file.suffix.lower() not in ALLOWED_SUFFIXES:
        raise ToolError("Only .eml and .msg files can be analyzed.")
    if not file.is_file():
        raise ToolError(f"No such file: {path}")
    data = file.read_bytes()
    if not data:
        raise ToolError("The file is empty.")
    if len(data) > MAX_FILE_BYTES:
        raise ToolError("The file is larger than the 25 MB limit.")
    boundary = uuid.uuid4().hex
    body = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{file.name}\"\r\n"
        "Content-Type: application/octet-stream\r\n\r\n"
    ).encode() + data + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        f"{api_url()}/analyze", data=body, method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    report = _request(req)
    return {key: report.get(key) for key in ("email_id", "verdict", "risk_score") if key in report}


def get_report(email_id: str) -> dict:
    if not email_id or not all(c.isalnum() or c in "-_" for c in email_id):
        raise ToolError("email_id looks invalid.")
    report = _request(urllib.request.Request(f"{api_url()}/investigations/{email_id}"))
    return {key: report.get(key) for key in ("email_id", "verdict", "risk_score", "subject", "final_assessment")
            if key in report}


def list_detection_rules() -> dict:
    rules = []
    for file in sorted(RULES_DIR.glob("*.toml")):
        data = tomllib.loads(file.read_text(encoding="utf-8"))
        rule = data.get("rule", {})
        actions = {a.get("action") for a in data.get("actions", [])}
        techniques = [t.get("id") for threat in data.get("threat", []) for t in threat.get("technique", [])]
        rules.append({
            "id": rule.get("id"), "name": rule.get("name"), "file": file.name,
            "severity": "high" if "kill_process" in actions else "medium",
            "techniques": techniques,
        })
    return {"count": len(rules), "rules": rules}


HANDLERS = {"analyze_email": analyze_email, "get_report": get_report, "list_detection_rules": list_detection_rules}


def call_tool(name: str, arguments: dict) -> dict:
    handler = HANDLERS.get(name)
    if handler is None:
        raise KeyError(name)
    try:
        result = handler(**arguments)
        return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}], "isError": False}
    except ToolError as exc:
        return {"content": [{"type": "text", "text": str(exc)}], "isError": True}
    except TypeError:
        return {"content": [{"type": "text", "text": f"Invalid arguments for {name}."}], "isError": True}


def handle(message: dict) -> dict | None:
    """Answer one JSON-RPC message. Notifications (no id) get no reply."""
    method, msg_id = message.get("method"), message.get("id")
    if msg_id is None:
        return None
    if method == "initialize":
        result = {"protocolVersion": PROTOCOL_VERSION, "capabilities": {"tools": {}}, "serverInfo": SERVER_INFO}
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": TOOLS}
    elif method == "tools/call":
        params = message.get("params") or {}
        try:
            result = call_tool(params.get("name", ""), params.get("arguments") or {})
        except KeyError:
            return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32602, "message": "Unknown tool"}}
    else:
        return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32601, "message": f"Method not found: {method}"}}
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            reply = handle(json.loads(line))
        except json.JSONDecodeError:
            reply = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}
        if reply is not None:
            sys.stdout.write(json.dumps(reply) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
