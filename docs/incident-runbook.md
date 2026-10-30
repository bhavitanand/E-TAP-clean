# E-TAP incident runbook

For the person (or agent) answering "E-TAP is down or acting strangely". Start with the two probes.

| Probe | Healthy answer | Meaning |
| --- | --- | --- |
| `GET /health` | `200 {"status":"ok"}` | The web process is up. |
| `GET /ready` | `200 {"status":"ready"}` | The database answers. A `503 {"status":"not_ready"}` means MongoDB is unreachable. |

## Cases
1. **No answer or a timeout on `/health`.** The process is down, or the host is waking from sleep (free tiers sleep when idle; the first request can take up to a minute). Try again after a minute. If it stays down, the hosting service needs a restart or a look at its logs; that is a human action.
2. **`/health` is fine, `/ready` is 503.** MongoDB Atlas is unreachable: check the cluster is running and that Network Access still allows the host, and that `MONGODB_URI` is current. Analyses cannot be stored until it is fixed.
3. **Both fine, but analyses are slow or incomplete.** An outside service is probably slow. VirusTotal and AbuseIPDB are rate limited; Gemini may be missing or rate limited, in which case E-TAP uses its offline explanation. Reports still complete, with fewer lookups. This is degraded, not down.
4. **Browser shows a network or CORS error but the probes are fine.** `ALLOWED_ORIGINS` on the API does not list the dashboard's address.
5. **Deeper (sandbox) analysis does nothing.** Only affects users who paired their own VM; the standard analysis is unaffected. Check the pairing page for the agent's status.

## Rules for responders
- Read-only checks first. Restarts, redeploys and configuration changes are decided by a person.
- Never paste keys, connection strings or `.env` contents into an issue.
- Say what you checked and what you did not.
