"""Tests for the E-TAP MCP server (mcp_server/etap_mcp_server.py)."""
import importlib.util
import json
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Thread

import pytest

SERVER = Path(__file__).resolve().parents[2] / "mcp_server" / "etap_mcp_server.py"
spec = importlib.util.spec_from_file_location("etap_mcp_server", SERVER)
mcp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mcp)


def rpc(method, params=None, msg_id=1):
    message = {"jsonrpc": "2.0", "id": msg_id, "method": method}
    if params is not None:
        message["params"] = params
    return mcp.handle(message)


@pytest.fixture()
def fake_api(monkeypatch):
    seen = {}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _send(self, payload, code=200):
            body = json.dumps(payload).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            seen["body"] = self.rfile.read(int(self.headers["Content-Length"]))
            seen["type"] = self.headers["Content-Type"]
            self._send({"email_id": "abc123", "verdict": "Likely Phishing", "risk_score": 88, "noise": "x"})

        def do_GET(self):
            if self.path.endswith("/missing"):
                self._send({"detail": "Investigation not found"}, 404)
            else:
                self._send({"email_id": "abc123", "verdict": "Suspicious", "risk_score": 45, "subject": "Hi"})

    server = HTTPServer(("127.0.0.1", 0), Handler)
    Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setenv("ETAP_API_URL", f"http://127.0.0.1:{server.server_port}")
    yield seen
    server.shutdown()


def test_initialize_and_tool_list():
    init = rpc("initialize", {"protocolVersion": mcp.PROTOCOL_VERSION})
    assert init["result"]["serverInfo"]["name"] == "etap"
    names = {t["name"] for t in rpc("tools/list")["result"]["tools"]}
    assert names == {"analyze_email", "get_report", "list_detection_rules"}


def test_notifications_get_no_reply():
    assert mcp.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None


def test_unknown_method_and_tool():
    assert rpc("nope")["error"]["code"] == -32601
    assert rpc("tools/call", {"name": "nope", "arguments": {}})["error"]["code"] == -32602


def test_list_detection_rules_matches_rule_files():
    result = rpc("tools/call", {"name": "list_detection_rules", "arguments": {}})["result"]
    data = json.loads(result["content"][0]["text"])
    assert data["count"] == len(list(mcp.RULES_DIR.glob("*.toml"))) >= 51
    assert {r["severity"] for r in data["rules"]} == {"high", "medium"}
    assert all(r["id"].startswith("etap-") for r in data["rules"])


def test_analyze_email_sends_file_and_trims_reply(tmp_path, fake_api):
    eml = tmp_path / "sample.eml"
    eml.write_bytes(b"From: a@b.c\r\nSubject: hi\r\n\r\nbody")
    result = rpc("tools/call", {"name": "analyze_email", "arguments": {"path": str(eml)}})["result"]
    assert result["isError"] is False
    assert json.loads(result["content"][0]["text"]) == {"email_id": "abc123", "verdict": "Likely Phishing", "risk_score": 88}
    assert b"filename=\"sample.eml\"" in fake_api["body"] and b"Subject: hi" in fake_api["body"]
    assert fake_api["type"].startswith("multipart/form-data; boundary=")


@pytest.mark.parametrize("name,content", [("evil.exe", b"MZ"), ("empty.eml", b"")])
def test_analyze_email_rejects_bad_files(tmp_path, name, content):
    file = tmp_path / name
    file.write_bytes(content)
    result = rpc("tools/call", {"name": "analyze_email", "arguments": {"path": str(file)}})["result"]
    assert result["isError"] is True


def test_analyze_email_missing_file():
    result = rpc("tools/call", {"name": "analyze_email", "arguments": {"path": "nowhere.eml"}})["result"]
    assert result["isError"] is True and "No such file" in result["content"][0]["text"]


def test_get_report_and_errors(fake_api):
    ok = rpc("tools/call", {"name": "get_report", "arguments": {"email_id": "abc123"}})["result"]
    assert json.loads(ok["content"][0]["text"])["risk_score"] == 45
    missing = rpc("tools/call", {"name": "get_report", "arguments": {"email_id": "missing"}})["result"]
    assert missing["isError"] is True and "404" in missing["content"][0]["text"]
    bad = rpc("tools/call", {"name": "get_report", "arguments": {"email_id": "../etc"}})["result"]
    assert bad["isError"] is True


def test_api_down_is_a_tool_error(monkeypatch):
    monkeypatch.setenv("ETAP_API_URL", "http://127.0.0.1:9")
    result = rpc("tools/call", {"name": "get_report", "arguments": {"email_id": "abc"}})["result"]
    assert result["isError"] is True and "Could not reach" in result["content"][0]["text"]


def test_stdio_round_trip():
    lines = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
    ]
    proc = subprocess.run([sys.executable, str(SERVER)], input="\n".join(json.dumps(m) for m in lines) + "\nnot json\n",
                          capture_output=True, text=True, timeout=30)
    replies = [json.loads(line) for line in proc.stdout.splitlines()]
    assert [r.get("id") for r in replies] == [1, 2, None]
    assert replies[2]["error"]["code"] == -32700
