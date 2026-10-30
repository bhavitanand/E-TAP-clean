# E-TAP MCP server

Lets an AI agent use E-TAP as a tool over the Model Context Protocol (stdio). Standard library only, Python 3.11+.

| Tool | What it does |
| --- | --- |
| `analyze_email` | Sends a `.eml` or `.msg` file from the workspace to the E-TAP API; returns `email_id`, `verdict` and `risk_score`. |
| `get_report` | Fetches a stored report by `email_id`. |
| `list_detection_rules` | Lists the behaviour rules (id, name, severity, ATT&CK ids). Works without the API. |

## Use with an MCP client
Most MCP clients accept a stdio server entry like this. Set `ETAP_API_URL` to your E-TAP API (the default is `http://127.0.0.1:5000`).
```json
{
  "mcpServers": {
    "etap": {
      "type": "stdio",
      "command": "python",
      "args": ["mcp_server/etap_mcp_server.py"],
      "env": { "ETAP_API_URL": "http://127.0.0.1:5000" }
    }
  }
}
```
Clients usually ask you to approve each tool before it runs.

## Try it by hand
```bash
python mcp_server/etap_mcp_server.py
{"jsonrpc":"2.0","id":1,"method":"tools/list"}
```

## Safety
- Only `.eml` and `.msg` files up to 25 MB are read, and only the file the agent names.
- The server never starts a VM and never writes anything; analysis is the API's static analysis (Standard).
- Tests: `backend/tests/test_mcp_server.py` (a stand-in API and a real stdio round trip).

## Not verified
Only tested against a stand-in API and a real stdio round trip; it has not been connected to a production MCP client session.
